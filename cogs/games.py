"""
cogs/games.py
Ekonomiyle entegre oyunlar: Blackjack, Slot Makinesi, Yazı-Tura,
Rus Ruleti, Adam Asmaca.
"""

import discord
from discord.ext import commands
import random
import asyncio
import datetime

from database import db
from utils.helpers import success_embed, error_embed, info_embed, Colors, format_number


class Games(commands.Cog, name="Oyunlar"):
    """Kumar ve eğlence oyunları."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.CURRENCY = "💰"
        self.CURRENCY_NAME = "Altın"

        # Adam asmaca için kelimeler
        self.HANGMAN_WORDS = [
            "discord", "python", "programlama", "yazılım", "bilgisayar",
            "internet", "veritabanı", "algoritma", "karakter", "sunucu",
            "moderatör", "geliştirici", "framework", "kütüphane", "arayüz",
            "işlemci", "bellek", "klavye", "monitör", "yazıcı", "müzik",
            "ekonomi", "bakiye", "ödül", "kuyruk", "oyuncu", "komut"
        ]
        # Adam asmaca görsel aşamaları
        self.HANGMAN_STAGES = [
            "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```",
        ]

    def _currency(self, amount: int) -> str:
        return f"{self.CURRENCY} **{format_number(amount)}** {self.CURRENCY_NAME}"

    def _create_card_deck(self) -> list:
        """52 kartlık standart deste oluşturur."""
        suits  = ["♠️", "♥️", "♦️", "♣️"]
        values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        return [{"suit": s, "value": v} for s in suits for v in values]

    def _card_value(self, card: dict) -> int:
        """Kartın sayısal değerini döndürür."""
        v = card["value"]
        if v in ("J", "Q", "K"):
            return 10
        if v == "A":
            return 11  # As ilk başta 11, gerekirse 1'e düşer
        return int(v)

    def _hand_value(self, hand: list) -> int:
        """Eldeki kartların toplam değerini hesaplar (As kuralıyla)."""
        total = sum(self._card_value(c) for c in hand)
        aces  = sum(1 for c in hand if c["value"] == "A")
        # As kuralı: 21'i geçiyorsa As 1 sayılır
        while total > 21 and aces:
            total -= 10
            aces  -= 1
        return total

    def _format_hand(self, hand: list) -> str:
        """Eldeki kartları emoji ile gösterir."""
        return "  ".join(f"[{c['value']}{c['suit']}]" for c in hand)

    # ─────────────────────────────────────────────
    # BLACKJACK
    # ─────────────────────────────────────────────

    @commands.command(name="blackjack", aliases=["bj"],
                      help="Blackjack oynar. Kullanım: !blackjack <miktar>")
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context, bet: int):
        """
        Klasik Blackjack oyunu.
        21'i geçmeden en yakın eli oluştur, krupiyeyi yen!
        """
        if bet <= 0:
            return await ctx.send(embed=error_embed("Geçerli bir bahis miktarı gir!"))

        data = await db.get_economy(ctx.author.id, ctx.guild.id)
        if data["balance"] < bet:
            return await ctx.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Cüzdanında yeterli para yok. Bakiyen: {self._currency(data['balance'])}"
            ))

        # Kartları dağıt
        deck = self._create_card_deck()
        random.shuffle(deck)
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        def build_embed(show_dealer: bool = False, result: str = None) -> discord.Embed:
            color = Colors.ECONOMY
            if result == "win":   color = Colors.SUCCESS
            elif result == "lose": color = Colors.ERROR
            elif result == "tie":  color = Colors.WARNING

            embed = discord.Embed(
                title="🃏 Blackjack",
                color=color,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(
                name=f"🃏 Senin El ({self._hand_value(player_hand)})",
                value=self._format_hand(player_hand),
                inline=False
            )
            if show_dealer:
                embed.add_field(
                    name=f"🤖 Krupiyer ({self._hand_value(dealer_hand)})",
                    value=self._format_hand(dealer_hand),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"🤖 Krupiyer (?)",
                    value=f"[{dealer_hand[0]['value']}{dealer_hand[0]['suit']}]  [❓]",
                    inline=False
                )
            embed.add_field(name="💵 Bahis", value=self._currency(bet))
            if result:
                messages = {
                    "win": f"🎉 Kazandın! +{self._currency(bet)}",
                    "lose": f"😞 Kaybettin! -{self._currency(bet)}",
                    "tie": "🤝 Beraberlik! Bahis iade edildi.",
                    "blackjack": f"🌟 BLACKJACK! +{self._currency(int(bet * 1.5))}"
                }
                embed.add_field(name="Sonuç",
                                value=messages.get(result, ""), inline=False)
            return embed

        # Blackjack kontrolü (ilk dağıtımda 21)
        if self._hand_value(player_hand) == 21:
            reward = int(bet * 1.5)
            await db.update_balance(ctx.author.id, ctx.guild.id, reward)
            return await ctx.send(embed=build_embed(show_dealer=True, result="blackjack"))

        # Oyuncu aksiyonları için butonlar
        class BlackjackView(discord.ui.View):
            def __init__(self_v):
                super().__init__(timeout=60)
                self_v.result = None

            @discord.ui.button(label="Kart Al (Hit)", style=discord.ButtonStyle.primary,
                               emoji="🃏")
            async def hit(self_v, interaction: discord.Interaction,
                          button: discord.ui.Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message(
                        "Bu oyun sana ait değil!", ephemeral=True
                    )
                player_hand.append(deck.pop())
                pv = self._hand_value(player_hand)

                if pv > 21:
                    # Battı
                    await db.update_balance(ctx.author.id, ctx.guild.id, -bet)
                    self_v.stop()
                    for child in self_v.children:
                        child.disabled = True
                    await interaction.response.edit_message(
                        embed=build_embed(show_dealer=True, result="lose"), view=self_v
                    )
                elif pv == 21:
                    # Tam 21
                    await self_v.stand_action(interaction)
                else:
                    await interaction.response.edit_message(
                        embed=build_embed(), view=self_v
                    )

            @discord.ui.button(label="Dur (Stand)", style=discord.ButtonStyle.secondary,
                               emoji="✋")
            async def stand(self_v, interaction: discord.Interaction,
                            button: discord.ui.Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message(
                        "Bu oyun sana ait değil!", ephemeral=True
                    )
                await self_v.stand_action(interaction)

            async def stand_action(self_v, interaction):
                # Krupiyer 17'nin altındaysa kart çeker
                while self._hand_value(dealer_hand) < 17:
                    dealer_hand.append(deck.pop())

                pv = self._hand_value(player_hand)
                dv = self._hand_value(dealer_hand)

                if dv > 21 or pv > dv:
                    result = "win"
                    await db.update_balance(ctx.author.id, ctx.guild.id, bet)
                elif pv == dv:
                    result = "tie"
                else:
                    result = "lose"
                    await db.update_balance(ctx.author.id, ctx.guild.id, -bet)

                self_v.stop()
                for child in self_v.children:
                    child.disabled = True
                await interaction.response.edit_message(
                    embed=build_embed(show_dealer=True, result=result), view=self_v
                )

            @discord.ui.button(label="Çift (Double)", style=discord.ButtonStyle.success,
                               emoji="💰")
            async def double_down(self_v, interaction: discord.Interaction,
                                  button: discord.ui.Button):
                nonlocal bet
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message(
                        "Bu oyun sana ait değil!", ephemeral=True
                    )
                # Çift bahis kontrolü
                d = await db.get_economy(ctx.author.id, ctx.guild.id)
                if d["balance"] < bet:
                    return await interaction.response.send_message(
                        "Çift bahis için yeterli paran yok!", ephemeral=True
                    )
                # Bir kart al, sonra dur
                player_hand.append(deck.pop())
                bet = bet * 2  # Double için bahisi ikiye katla
                # Double için ekstra bahis çekilir
                await db.update_balance(ctx.author.id, ctx.guild.id, -bet)
                await self_v.stand_action(interaction)

        view = BlackjackView()
        await ctx.send(embed=build_embed(), view=view)

    # ─────────────────────────────────────────────
    # SLOT MAKİNESİ
    # ─────────────────────────────────────────────

    @commands.command(name="slot", help="Slot makinesi oynar. !slot <miktar>")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slot(self, ctx: commands.Context, bet: int):
        """
        Slot makinesi!
        3 aynı sembol jackpot!
        """
        if bet <= 0:
            return await ctx.send(embed=error_embed("Geçerli bir bahis gir!"))
        if bet > 10000:
            return await ctx.send(embed=error_embed("Maksimum bahis: 10,000!"))

        data = await db.get_economy(ctx.author.id, ctx.guild.id)
        if data["balance"] < bet:
            return await ctx.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Bakiyen: {self._currency(data['balance'])}"
            ))

        # Semboller ve ağırlıkları (nadir olanlar daha az ağırlıklı)
        symbols = ["🍒", "🍋", "🍇", "🍀", "⭐", "💎", "🎰", "7️⃣"]
        weights = [30,    25,    20,    12,    7,    4,    1.5,  0.5]

        # 3 sembol çek
        results = random.choices(symbols, weights=weights, k=3)

        # Kazanç çarpanları
        multipliers = {
            "🍒": 2,   "🍋": 2.5,  "🍇": 3,
            "🍀": 4,   "⭐": 5,    "💎": 10,
            "🎰": 25,  "7️⃣": 50
        }

        # Sonuç hesabı
        if results[0] == results[1] == results[2]:
            # 3 aynı: Jackpot!
            multiplier = multipliers.get(results[0], 2)
            winnings   = int(bet * multiplier) - bet
            await db.update_balance(ctx.author.id, ctx.guild.id, winnings)
            color   = Colors.SUCCESS
            outcome = f"🎉 **JACKPOT!** ×{multiplier} kazandın! +{self._currency(winnings)}"
        elif results[0] == results[1] or results[1] == results[2]:
            # 2 aynı: Küçük kazanç
            winnings = int(bet * 0.5)
            await db.update_balance(ctx.author.id, ctx.guild.id, winnings)
            color   = Colors.WARNING
            outcome = f"✨ İki eşleşme! +{self._currency(winnings)}"
        else:
            # Kaybetti
            await db.update_balance(ctx.author.id, ctx.guild.id, -bet)
            color   = Colors.ERROR
            outcome = f"😞 Kaybettin! -{self._currency(bet)}"

        embed = discord.Embed(
            title="🎰 Slot Makinesi",
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name="Sonuç",
            value=f"╔══════════════╗\n║ {results[0]}  {results[1]}  {results[2]} ║\n╚══════════════╝",
            inline=False
        )
        embed.add_field(name="💵 Bahis", value=self._currency(bet))
        embed.add_field(name="📊 Durum", value=outcome, inline=False)
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # YAZI-TURA
    # ─────────────────────────────────────────────

    @commands.command(name="yazıtura", aliases=["coinflip", "flip"],
                      help="Yazı tura atar. !yazıtura <yazı/tura> <miktar>")
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx: commands.Context, choice: str, bet: int):
        """
        Yazı-tura oyunu.
        Kullanım: !yazıtura yazı 500 veya !yazıtura tura 1000
        """
        choice = choice.lower()
        if choice not in ("yazı", "tura", "yazi", "heads", "tails"):
            return await ctx.send(embed=error_embed(
                "Geçersiz Seçim",
                "Sadece `yazı` veya `tura` girebilirsin."
            ))

        if bet <= 0:
            return await ctx.send(embed=error_embed("Geçerli bir bahis gir!"))

        data = await db.get_economy(ctx.author.id, ctx.guild.id)
        if data["balance"] < bet:
            return await ctx.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Bakiyen: {self._currency(data['balance'])}"
            ))

        # Sonuç belirle
        result = random.choice(["yazı", "tura"])
        choice_normalized = "yazı" if choice in ("yazı", "yazi", "heads") else "tura"

        if choice_normalized == result:
            await db.update_balance(ctx.author.id, ctx.guild.id, bet)
            embed = success_embed(
                "Kazandın! 🎉",
                f"Madeni para **{result}** geldi!\n"
                f"Bahsin: {self._currency(bet)} → Kazanç: +{self._currency(bet)}"
            )
        else:
            await db.update_balance(ctx.author.id, ctx.guild.id, -bet)
            embed = error_embed(
                "Kaybettin! 😞",
                f"Madeni para **{result}** geldi, sen **{choice_normalized}** seçmiştin.\n"
                f"Kayıp: -{self._currency(bet)}"
            )

        embed.color = Colors.ECONOMY
        coin_emoji = "🪙"
        embed.set_author(name=f"{coin_emoji} Yazı-Tura")
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # RUS RULETİ
    # ─────────────────────────────────────────────

    @commands.command(name="rusruleti", aliases=["rr", "russianroulette"],
                      help="Rus ruleti oynar. !rusruleti <miktar>")
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def russian_roulette(self, ctx: commands.Context, bet: int):
        """
        Rus Ruleti! 6 odadan birinde kurşun var.
        Hayatta kalırsan 5x kazanırsın, ölürsen her şeyi kaybedersin!
        """
        if bet <= 0:
            return await ctx.send(embed=error_embed("Geçerli bir bahis gir!"))

        data = await db.get_economy(ctx.author.id, ctx.guild.id)
        if data["balance"] < bet:
            return await ctx.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Bakiyen: {self._currency(data['balance'])}"
            ))

        # 1/6 ihtimalle kurşun
        bullet_chamber = random.randint(1, 6)
        fired_chamber  = random.randint(1, 6)

        # Gerilim oluştur
        await ctx.send(embed=discord.Embed(
            title="🔫 Rus Ruleti",
            description=(
                f"**{ctx.author.mention}** silahı kafasına dayadı...\n"
                f"6 odadan 1'inde kurşun var...\n"
                f"Bahis: {self._currency(bet)}\n\n"
                "**`Tetik çekiliyor...`** 🎯"
            ),
            color=Colors.MOD
        ))
        await asyncio.sleep(3)

        if bullet_chamber == fired_chamber:
            # Öldü — tüm cüzdan bakiyesi gidebilir de, bet kadar al
            loss = min(bet, data["balance"])
            await db.update_balance(ctx.author.id, ctx.guild.id, -loss)
            embed = discord.Embed(
                title="💀 BANG! Öldün!",
                description=(
                    f"**BANG!** 💥\n"
                    f"Kurşun {bullet_chamber}. odadaydı!\n"
                    f"Kaybettin: -{self._currency(loss)}"
                ),
                color=Colors.ERROR
            )
            embed.set_footer(text="Bir dahaki sefere daha şanslı olursun...")
        else:
            # Hayatta kaldı — 5x kazanç
            winnings = bet * 4  # Bahis geri + 4x üstü
            await db.update_balance(ctx.author.id, ctx.guild.id, winnings)
            embed = discord.Embed(
                title="😅 Hayatta Kaldın!",
                description=(
                    f"**Tık!** Boş oda!\n"
                    f"Kurşun {bullet_chamber}. odadaydı, sen {fired_chamber}. odayı çekttin!\n"
                    f"Kazanç: +{self._currency(winnings)} (×5)"
                ),
                color=Colors.SUCCESS
            )
            embed.set_footer(text="Şanslı adamsın!")

        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # ADAM ASMACA
    # ─────────────────────────────────────────────

    @commands.command(name="adamasmaca", aliases=["hangman"],
                      help="Adam asmaca oynar.")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def hangman(self, ctx: commands.Context):
        """
        Adam asmaca oyunu! Kelimeyi 7 hamlede tahmin et.
        Doğru tahmin: +300 altın | Yanlış: Hiç ödül yok.
        """
        word      = random.choice(self.HANGMAN_WORDS).upper()
        guessed   = set()
        wrong     = 0
        max_wrong = 6  # 7 aşama, 0'dan başlıyor

        def get_display() -> str:
            """Kelimenin mevcut görünümünü döndürür."""
            return " ".join(letter if letter in guessed else "_" for letter in word)

        def build_embed() -> discord.Embed:
            embed = discord.Embed(
                title="🎯 Adam Asmaca",
                color=Colors.INFO,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Kelime", value=f"```{get_display()}```", inline=False)
            embed.add_field(name="Adam", value=self.HANGMAN_STAGES[wrong], inline=False)
            embed.add_field(
                name="Yanlış Harfler",
                value=" ".join(guessed - set(word)) or "Henüz yok",
                inline=True
            )
            embed.add_field(name="Kalan Hak", value=str(max_wrong - wrong), inline=True)
            embed.set_footer(text=f"{ctx.author.display_name} | Harf girmek için yaz")
            return embed

        msg = await ctx.send(embed=build_embed())

        while wrong <= max_wrong and set(word) - guessed:
            def check(m):
                return (m.author == ctx.author and
                        m.channel == ctx.channel and
                        len(m.content) == 1 and
                        m.content.isalpha())

            try:
                reply = await self.bot.wait_for("message", timeout=30, check=check)
            except asyncio.TimeoutError:
                return await ctx.send(embed=error_embed(
                    "Süre Doldu",
                    f"Kelime: **{word}**"
                ))

            letter = reply.content.upper()
            await reply.delete()

            if letter in guessed:
                await ctx.send(f"⚠️ `{letter}` harfini zaten denedin!", delete_after=3)
                continue

            guessed.add(letter)

            if letter in word:
                # Doğru harf
                if set(word) - guessed == set():
                    # Kazandı
                    await db.update_balance(ctx.author.id, ctx.guild.id, 300)
                    win_embed = success_embed(
                        "Tebrikler! 🎉",
                        f"Kelime: **{word}**\nKazanç: +💰 **300** Altın"
                    )
                    await msg.edit(embed=build_embed())
                    return await ctx.send(embed=win_embed)
            else:
                wrong += 1
                if wrong > max_wrong:
                    # Kaybetti
                    lose_embed = error_embed(
                        "Oyun Bitti! 💀",
                        f"Kelime: **{word}**\nHakkın bitti!"
                    )
                    await msg.edit(embed=build_embed())
                    return await ctx.send(embed=lose_embed)

            await msg.edit(embed=build_embed())

    # ─────────────────────────────────────────────
    # ROB (SOYGUN)
    # ─────────────────────────────────────────────

    @commands.command(name="soy", aliases=["rob"],
                      help="Başka birinin parasını çalmaya çalışırsın.")
    @commands.guild_only()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def rob(self, ctx: commands.Context, member: discord.Member):
        """
        Riskli bir soygun! 40% başarı şansı.
        Başarırsan hedefin bakiyesinin %10-30'unu çalarsın.
        Başaramazsan 200 altın ceza ödersin.
        """
        if member == ctx.author:
            return await ctx.send(embed=error_embed("Kendini soyamazsın!"))
        if member.bot:
            return await ctx.send(embed=error_embed("Botları soyamazsın!"))

        target_data = await db.get_economy(member.id, ctx.guild.id)
        if target_data["balance"] < 200:
            return await ctx.send(embed=error_embed(
                "Değmez",
                f"**{member.display_name}** yeterince parası yok (min. 200 altın)."
            ))

        robber_data = await db.get_economy(ctx.author.id, ctx.guild.id)
        fine = 200  # Yakalanırsa ceza

        # %40 başarı şansı
        if random.random() < 0.4:
            # Başarılı soygun
            steal_pct  = random.uniform(0.1, 0.3)
            steal_amt  = int(target_data["balance"] * steal_pct)
            await db.update_balance(member.id, ctx.guild.id, -steal_amt)
            await db.update_balance(ctx.author.id, ctx.guild.id, steal_amt)
            embed = success_embed(
                "Soygun Başarılı! 🦹",
                f"**{member.mention}** kullanıcısından **{self._currency(steal_amt)}** çaldın!"
            )
        else:
            # Yakalandı
            actual_fine = min(fine, robber_data["balance"])
            await db.update_balance(ctx.author.id, ctx.guild.id, -actual_fine)
            embed = error_embed(
                "Yakalandın! 👮",
                f"Soygun başarısız! Polise {self._currency(actual_fine)} ceza ödedi."
            )

        embed.color = Colors.ECONOMY
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Cog'u bota yükle."""
    await bot.add_cog(Games(bot))