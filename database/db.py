"""
database/db.py
Tüm veritabanı işlemlerini yöneten merkezi modül.
SQLite kullanılarak aiosqlite ile asenkron erişim sağlanır.
"""

import aiosqlite
import os

# Veritabanı dosyasının yolu
DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")


async def init_db():
    """
    Veritabanını başlatır, tablolar yoksa oluşturur.
    Bot ilk çalıştığında bu fonksiyon çağrılır.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Kullanıcı ekonomi tablosu
        await db.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                user_id   INTEGER PRIMARY KEY,
                guild_id  INTEGER NOT NULL,
                balance   INTEGER DEFAULT 0,
                bank      INTEGER DEFAULT 0,
                last_daily TEXT DEFAULT NULL
            )
        """)

        # Seviye/XP tablosu
        await db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                user_id    INTEGER,
                guild_id   INTEGER,
                xp         INTEGER DEFAULT 0,
                level      INTEGER DEFAULT 0,
                messages   INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Uyarı (warn) tablosu
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                guild_id   INTEGER NOT NULL,
                moderator  INTEGER NOT NULL,
                reason     TEXT,
                timestamp  TEXT
            )
        """)

        # Moderasyon ayarları tablosu (filtre, log kanalları vs.)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id          INTEGER PRIMARY KEY,
                log_channel       INTEGER DEFAULT NULL,
                join_leave_log    INTEGER DEFAULT NULL,
                voice_log         INTEGER DEFAULT NULL,
                mod_log           INTEGER DEFAULT NULL,
                prefix            TEXT DEFAULT '!',
                profanity_filter  INTEGER DEFAULT 0,
                link_filter       INTEGER DEFAULT 0
            )
        """)

        await db.commit()
    print("[DB] Veritabanı başarıyla başlatıldı.")


# ─────────────────────────────────────────────
# EKONOMİ FONKSİYONLARI
# ─────────────────────────────────────────────

async def get_economy(user_id: int, guild_id: int) -> dict:
    """Bir kullanıcının ekonomi verisini döndürür, yoksa oluşturur."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM economy WHERE user_id=? AND guild_id=?",
            (user_id, guild_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                # Kullanıcı yoksa yeni kayıt oluştur
                await db.execute(
                    "INSERT INTO economy (user_id, guild_id) VALUES (?, ?)",
                    (user_id, guild_id)
                )
                await db.commit()
                return {"user_id": user_id, "guild_id": guild_id,
                        "balance": 0, "bank": 0, "last_daily": None}
            return dict(row)


async def update_balance(user_id: int, guild_id: int, amount: int):
    """Kullanıcının cüzdan bakiyesini günceller (eksi değer mümkün)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE economy SET balance = balance + ? WHERE user_id=? AND guild_id=?",
            (amount, user_id, guild_id)
        )
        await db.commit()


async def set_balance(user_id: int, guild_id: int, amount: int):
    """Kullanıcının bakiyesini belirli bir değere ayarlar."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE economy SET balance=? WHERE user_id=? AND guild_id=?",
            (amount, user_id, guild_id)
        )
        await db.commit()


async def update_bank(user_id: int, guild_id: int, amount: int):
    """Kullanıcının banka bakiyesini günceller."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE economy SET bank = bank + ? WHERE user_id=? AND guild_id=?",
            (amount, user_id, guild_id)
        )
        await db.commit()


async def set_last_daily(user_id: int, guild_id: int, timestamp: str):
    """Günlük ödül için son alım zamanını kaydeder."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE economy SET last_daily=? WHERE user_id=? AND guild_id=?",
            (timestamp, user_id, guild_id)
        )
        await db.commit()


async def get_leaderboard(guild_id: int, limit: int = 10) -> list:
    """Sunucudaki en zengin kullanıcıları döndürür."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT user_id, balance + bank AS total
               FROM economy WHERE guild_id=?
               ORDER BY total DESC LIMIT ?""",
            (guild_id, limit)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


# ─────────────────────────────────────────────
# SEVİYE FONKSİYONLARI
# ─────────────────────────────────────────────

async def get_level(user_id: int, guild_id: int) -> dict:
    """Kullanıcının seviye verisini döndürür."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM levels WHERE user_id=? AND guild_id=?",
            (user_id, guild_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                await db.execute(
                    "INSERT INTO levels (user_id, guild_id) VALUES (?, ?)",
                    (user_id, guild_id)
                )
                await db.commit()
                return {"user_id": user_id, "guild_id": guild_id,
                        "xp": 0, "level": 0, "messages": 0}
            return dict(row)


async def add_xp(user_id: int, guild_id: int, xp: int) -> dict:
    """
    Kullanıcıya XP ekler.
    Seviye atlandıysa yeni level'ı döndürür, yoksa None döner.
    """
    data = await get_level(user_id, guild_id)
    new_xp = data["xp"] + xp
    new_messages = data["messages"] + 1
    current_level = data["level"]

    # Seviye atlamak için gereken XP formülü: 5 * (level^2) + 50*level + 100
    xp_needed = 5 * (current_level ** 2) + 50 * current_level + 100
    leveled_up = False
    new_level = current_level

    if new_xp >= xp_needed:
        new_xp -= xp_needed
        new_level = current_level + 1
        leveled_up = True

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE levels SET xp=?, level=?, messages=?
               WHERE user_id=? AND guild_id=?""",
            (new_xp, new_level, new_messages, user_id, guild_id)
        )
        await db.commit()

    if leveled_up:
        return {"leveled_up": True, "new_level": new_level}
    return {"leveled_up": False}


async def get_level_leaderboard(guild_id: int, limit: int = 10) -> list:
    """XP bazlı sıralamayı döndürür."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT user_id, level, xp, messages
               FROM levels WHERE guild_id=?
               ORDER BY level DESC, xp DESC LIMIT ?""",
            (guild_id, limit)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


# ─────────────────────────────────────────────
# UYARI FONKSİYONLARI
# ─────────────────────────────────────────────

async def add_warning(user_id: int, guild_id: int, moderator_id: int,
                      reason: str, timestamp: str) -> int:
    """Kullanıcıya uyarı ekler, yeni uyarı ID'sini döner."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO warnings (user_id, guild_id, moderator, reason, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, guild_id, moderator_id, reason, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_warnings(user_id: int, guild_id: int) -> list:
    """Kullanıcının tüm uyarılarını listeler."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM warnings WHERE user_id=? AND guild_id=? ORDER BY id DESC",
            (user_id, guild_id)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def clear_warnings(user_id: int, guild_id: int):
    """Kullanıcının tüm uyarılarını siler."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM warnings WHERE user_id=? AND guild_id=?",
            (user_id, guild_id)
        )
        await db.commit()


# ─────────────────────────────────────────────
# SUNUCU AYARLARI FONKSİYONLARI
# ─────────────────────────────────────────────

async def get_guild_settings(guild_id: int) -> dict:
    """Sunucu ayarlarını döndürür."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                await db.execute(
                    "INSERT INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
                )
                await db.commit()
                return {"guild_id": guild_id, "log_channel": None,
                        "join_leave_log": None, "voice_log": None,
                        "mod_log": None, "prefix": "!",
                        "profanity_filter": 0, "link_filter": 0}
            return dict(row)


async def update_guild_setting(guild_id: int, key: str, value):
    """Belirli bir sunucu ayarını günceller."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE guild_settings SET {key}=? WHERE guild_id=?",
            (value, guild_id)
        )
        await db.commit()