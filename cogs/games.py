"""
cogs/games.py
Ekonomiyle entegre oyunlar — Slash komutlarına geçirildi.
Blackjack, Slot Makinesi, Yazı-Tura, Rus Ruleti, Adam Asmaca, Soygun.
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import datetime

from database import db
from utils.helpers import success_embed, error_embed, info_embed, Colors, format_number


class Games(commands.Cog, name="Oyunlar"):
    """Kumar ve eğlence oyunları."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.CURRENCY      = "💰"
        self.CURRENCY_NAME = "Altın"

        self.HANGMAN_WORDS = [
            "discord", "python", "programlama", "yazılım", "bilgisayar",
            "internet", "veritabanı", "algoritma", "karakter", "sunucu",
            "moderatör", "geliştirici", "framework", "kütüphane", "arayüz",
            "işlemci", "bellek", "klavye", "monitör", "yazıcı", "müzik",
            "ekonomi", "bakiye", "ödül", "kuyruk", "oyuncu", "komut"
        ]
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
        suits  = ["♠️", "♥️", "♦️", "♣️"]
        values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        return [{"suit": s, "value": v} for s in suits for v in values]

    def _card_value(self, card: dict) -> int:
        v = card["value"]
        if v in ("J", "Q", "K"): return 10
        if v == "A":              return 11
        return int(v)

    def _hand_value(self, hand: list) -> int:
        total = sum(self._card_value(c) for c in hand)
        aces  = sum(1 for c in hand if c["value"] == "A")
        while total > 21 and aces:
            total -= 10
            aces  -= 1
        return total

    def _format_hand(self, hand: list) -> str:
        return "  ".join(f"[{c['value']}{c['suit']}]" for c in hand)

    # ── BLACKJACK ────────────────────────────────────────────────────────

    @app_commands.command(name="blackjack", description="Blackjack oynar.")
    @app_commands.guild_only()
    @app_commands.describe(bahis="Yatırmak istediğin bahis miktarı")
    async def blackjack(self, interaction: discord.Interaction, bahis: int):
        await interaction.response.defer()

        if bahis <= 0:
            return await interaction.followup.send(
                embed=error_embed("Geçerli bir bahis miktarı gir!"), ephemeral=True)

        data = await db.get_economy(interaction.user.id, interaction.guild.id)
        if data["balance"] < bahis:
            return await interaction.followup.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Cüzdanında yeterli para yok. Bakiyen: {self._currency(data['balance'])}"
            ), ephemeral=True)

        deck = self._create_card_deck()
        random.shuffle(deck)
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        bet = bahis  # mutable reference için nonlocal kullanacağız

        def build_embed(show_dealer: bool = False, result: str = None) -> discord.Embed:
            color = Colors.ECONOMY
            if result == "win":       color = Colors.SUCCESS
            elif result == "lose":    color = Colors.ERROR
            elif result == "tie":     color = Colors.WARNING

            embed = discord.Embed(title="🃏 Blackjack", color=color,
                                  timestamp=datetime.datetime.utcnow())
            embed.add_field(
                name=f"🃏 Senin El ({self._hand_value(player_hand)})",
                value=self._format_hand(player_hand), inline=False)
            if show_dealer:
                embed.add_field(
                    name=f"🤖 Krupiyer ({self._hand_value(dealer_hand)})",
                    value=self._format_hand(dealer_hand), inline=False)
            else:
                embed.add_field(
                    name="🤖 Krupiyer (?)",
                    value=f"[{dealer_hand[0]['value']}{dealer_hand[0]['suit']}]  [❓]",
                    inline=False)
            embed.add_field(name="💵 Bahis", value=self._currency(bet))
            if result:
                msgs = {
                    "win":       f"🎉 Kazandın! +{self._currency(bet)}",
                    "lose":      f"😞 Kaybettin! -{self._currency(bet)}",
                    "tie":       "🤝 Beraberlik! Bahis iade edildi.",
                    "blackjack": f"🌟 BLACKJACK! +{self._currency(int(bet * 1.5))}"
                }
                embed.add_field(name="Sonuç", value=msgs.get(result, ""), inline=False)
            return embed

        if self._hand_value(player_hand) == 21:
            reward = int(bet * 1.5)
            await db.update_balance(interaction.user.id, interaction.guild.id, reward)
            return await interaction.followup.send(
                embed=build_embed(show_dealer=True, result="blackjack"))

        # Outer scope'ta bet'i takip et
        current_bet = [bet]

        class BlackjackView(discord.ui.View):
            def __init__(self_v):
                super().__init__(timeout=60)

            async def _finalize(self_v, interaction_btn: discord.Interaction, result: str):
                self_v.stop()
                for child in self_v.children:
                    child.disabled = True
                if result == "win":
                    await db.update_balance(
                        interaction.user.id, interaction.guild.id, current_bet[0])
                elif result == "lose":
                    await db.update_balance(
                        interaction.user.id, interaction.guild.id, -current_bet[0])
                embed = build_embed(show_dealer=True, result=result)
                if interaction_btn.response.is_done():
                    await interaction_btn.message.edit(embed=embed, view=self_v)
                else:
                    await interaction_btn.response.edit_message(embed=embed, view=self_v)

            async def _stand_logic(self_v, interaction_btn):
                while self._hand_value(dealer_hand) < 17:
                    dealer_hand.append(deck.pop())
                pv = self._hand_value(player_hand)
                dv = self._hand_value(dealer_hand)
                if dv > 21 or pv > dv:   result = "win"
                elif pv == dv:            result = "tie"
                else:                     result = "lose"
                await self_v._finalize(interaction_btn, result)

            @discord.ui.button(label="Kart Al (Hit)", style=discord.ButtonStyle.primary, emoji="🃏")
            async def hit(self_v, interaction_btn: discord.Interaction,
                          button: discord.ui.Button):
                if interaction_btn.user.id != interaction.user.id:
                    return await interaction_btn.response.send_message(
                        "Bu oyun sana ait değil!", ephemeral=True)
                player_hand.append(deck.pop())
                pv = self._hand_value(player_hand)
                if pv > 21:
                    await self_v._finalize(interaction_btn, "lose")
                elif pv == 21:
                    await self_v._stand_logic(interaction_btn)
                else:
                    await interaction_btn.response.edit_message(embed=build_embed(), view=self_v)

            @discord.ui.button(label="Dur (Stand)", style=discord.ButtonStyle.secondary, emoji="✋")
            async def stand(self_v, interaction_btn: discord.Interaction,
                            button: discord.ui.Button):
                if interaction_btn.user.id != interaction.user.id:
                    return await interaction_btn.response.send_message(
                        "Bu oyun sana ait değil!", ephemeral=True)
                await self_v._stand_logic(interaction_btn)

            @discord.ui.button(label="Çift (Double)", style=discord.ButtonStyle.success, emoji="💰")
            async def double_down(self_v, interaction_btn: discord.Interaction,
                                  button: discord.ui.Button):
                if interaction_btn.user.id != interaction.user.id:
                    return await interaction_btn.response.send_message(
                        "Bu oyun sana ait değil!", ephemeral=True)
                d = await db.get_economy(interaction.user.id, interaction.guild.id)
                if d["balance"] < current_bet[0]:
                    return await interaction_btn.response.send_message(
                        "Çift bahis için yeterli paran yok!", ephemeral=True)
                player_hand.append(deck.pop())
                current_bet[0] = current_bet[0] * 2
                await self_v._stand_logic(interaction_btn)

        view = BlackjackView()
        await interaction.followup.send(embed=build_embed(), view=view)

    # ── SLOT MAKİNESİ ────────────────────────────────────────────────────

    @app_commands.command(name="slot", description="Slot makinesi oynar.")
    @app_commands.guild_only()
    @app_commands.describe(bahis="Bahis miktarı (max 10.000)")
    async def slot(self, interaction: discord.Interaction, bahis: int):
        await interaction.response.defer()

        if bahis <= 0:
            return await interaction.followup.send(
                embed=error_embed("Geçerli bir bahis gir!"), ephemeral=True)
        if bahis > 10000:
            return await interaction.followup.send(
                embed=error_embed("Maksimum bahis: 10,000!"), ephemeral=True)

        data = await db.get_economy(interaction.user.id, interaction.guild.id)
        if data["balance"] < bahis:
            return await interaction.followup.send(embed=error_embed(
                "Yetersiz Bakiye", f"Bakiyen: {self._currency(data['balance'])}"
            ), ephemeral=True)

        symbols = ["🍒", "🍋", "🍇", "🍀", "⭐", "💎", "🎰", "7️⃣"]
        weights = [30,    25,    20,    12,    7,    4,    1.5,  0.5]
        results = random.choices(symbols, weights=weights, k=3)

        multipliers = {
            "🍒": 2,  "🍋": 2.5, "🍇": 3,
            "🍀": 4,  "⭐": 5,   "💎": 10,
            "🎰": 25, "7️⃣": 50
        }

        if results[0] == results[1] == results[2]:
            multiplier = multipliers.get(results[0], 2)
            winnings   = int(bahis * multiplier) - bahis
            await db.update_balance(interaction.user.id, interaction.guild.id, winnings)
            color   = Colors.SUCCESS
            outcome = f"🎉 **JACKPOT!** ×{multiplier} kazandın! +{self._currency(winnings)}"
        elif results[0] == results[1] or results[1] == results[2]:
            winnings = int(bahis * 0.5)
            await db.update_balance(interaction.user.id, interaction.guild.id, winnings)
            color   = Colors.WARNING
            outcome = f"✨ İki eşleşme! +{self._currency(winnings)}"
        else:
            await db.update_balance(interaction.user.id, interaction.guild.id, -bahis)
            color   = Colors.ERROR
            outcome = f"😞 Kaybettin! -{self._currency(bahis)}"

        embed = discord.Embed(title="🎰 Slot Makinesi", color=color,
                              timestamp=datetime.datetime.utcnow())
        embed.add_field(
            name="Sonuç",
            value=f"╔══════════════╗\n║ {results[0]}  {results[1]}  {results[2]} ║\n╚══════════════╝",
            inline=False
        )
        embed.add_field(name="💵 Bahis", value=self._currency(bahis))
        embed.add_field(name="📊 Durum", value=outcome, inline=False)
        await interaction.followup.send(embed=embed)

    # ── YAZI-TURA ────────────────────────────────────────────────────────

    @app_commands.command(name="yazıtura", description="Yazı tura atar.")
    @app_commands.guild_only()
    @app_commands.describe(seçim="Yazı veya tura", bahis="Bahis miktarı")
    @app_commands.choices(seçim=[
        app_commands.Choice(name="Yazı", value="yazı"),
        app_commands.Choice(name="Tura", value="tura"),
    ])
    async def coinflip(self, interaction: discord.Interaction,
                       seçim: str, bahis: int):
        await interaction.response.defer()

        if bahis <= 0:
            return await interaction.followup.send(
                embed=error_embed("Geçerli bir bahis gir!"), ephemeral=True)

        data = await db.get_economy(interaction.user.id, interaction.guild.id)
        if data["balance"] < bahis:
            return await interaction.followup.send(embed=error_embed(
                "Yetersiz Bakiye", f"Bakiyen: {self._currency(data['balance'])}"
            ), ephemeral=True)

        result = random.choice(["yazı", "tura"])
        if seçim == result:
            await db.update_balance(interaction.user.id, interaction.guild.id, bahis)
            embed = success_embed(
                "Kazandın! 🎉",
                f"Madeni para **{result}** geldi!\n"
                f"Bahsin: {self._currency(bahis)} → Kazanç: +{self._currency(bahis)}"
            )
        else:
            await db.update_balance(interaction.user.id, interaction.guild.id, -bahis)
            embed = error_embed(
                "Kaybettin! 😞",
                f"Madeni para **{result}** geldi, sen **{seçim}** seçmiştin.\n"
                f"Kayıp: -{self._currency(bahis)}"
            )
        embed.color = Colors.ECONOMY
        embed.set_author(name="🪙 Yazı-Tura")
        await interaction.followup.send(embed=embed)

    # ── RUS RULETİ ───────────────────────────────────────────────────────

    @app_commands.command(name="rusruleti", description="Rus ruleti oynar. Yüksek risk, yüksek ödül!")
    @app_commands.guild_only()
    @app_commands.describe(bahis="Bahis miktarı")
    async def russian_roulette(self, interaction: discord.Interaction, bahis: int):
        await interaction.response.defer()

        if bahis <= 0:
            return await interaction.followup.send(
                embed=error_embed("Geçerli bir bahis gir!"), ephemeral=True)

        data = await db.get_economy(interaction.user.id, interaction.guild.id)
        if data["balance"] < bahis:
            return await interaction.followup.send(embed=error_embed(
                "Yetersiz Bakiye", f"Bakiyen: {self._currency(data['balance'])}"
            ), ephemeral=True)

        bullet_chamber = random.randint(1, 6)
        fired_chamber  = random.randint(1, 6)

        await interaction.followup.send(embed=discord.Embed(
            title="🔫 Rus Ruleti",
            description=(
                f"**{interaction.user.mention}** silahı kafasına dayadı...\n"
                f"6 odadan 1'inde kurşun var...\n"
                f"Bahis: {self._currency(bahis)}\n\n"
                "**`Tetik çekiliyor...`** 🎯"
            ),
            color=Colors.MOD
        ))
        await asyncio.sleep(3)

        if bullet_chamber == fired_chamber:
            loss = min(bahis, data["balance"])
            await db.update_balance(interaction.user.id, interaction.guild.id, -loss)
            embed = discord.Embed(
                title="💀 BANG! Öldün!",
                description=(
                    f"**BANG!** 💥\nKurşun {bullet_chamber}. odadaydı!\n"
                    f"Kaybettin: -{self._currency(loss)}"
                ),
                color=Colors.ERROR
            )
            embed.set_footer(text="Bir dahaki sefere daha şanslı olursun...")
        else:
            winnings = bahis * 4
            await db.update_balance(interaction.user.id, interaction.guild.id, winnings)
            embed = discord.Embed(
                title="😅 Hayatta Kaldın!",
                description=(
                    f"**Tık!** Boş oda!\n"
                    f"Kurşun {bullet_chamber}. odadaydı, sen {fired_chamber}. odayı çektin!\n"
                    f"Kazanç: +{self._currency(winnings)} (×5)"
                ),
                color=Colors.SUCCESS
            )
            embed.set_footer(text="Şanslı adamsın!")

        await interaction.channel.send(embed=embed)

    # ── ADAM ASMACA ──────────────────────────────────────────────────────

    @app_commands.command(name="adamasmaca", description="Adam asmaca oynar. Kelimeyi 7 hamlede tahmin et!")
    @app_commands.guild_only()
    async def hangman(self, interaction: discord.Interaction):
        await interaction.response.defer()

        word      = random.choice(self.HANGMAN_WORDS).upper()
        guessed   = set()
        wrong     = 0
        max_wrong = 6

        def get_display() -> str:
            return " ".join(letter if letter in guessed else "_" for letter in word)

        def build_embed() -> discord.Embed:
            embed = discord.Embed(
                title="🎯 Adam Asmaca",
                color=Colors.INFO,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Kelime", value=f"```{get_display()}```", inline=False)
            embed.add_field(name="Adam",   value=self.HANGMAN_STAGES[wrong], inline=False)
            embed.add_field(
                name="Yanlış Harfler",
                value=" ".join(guessed - set(word)) or "Henüz yok",
                inline=True
            )
            embed.add_field(name="Kalan Hak", value=str(max_wrong - wrong), inline=True)
            embed.set_footer(text=f"{interaction.user.display_name} | Kanala harf yaz")
            return embed

        msg = await interaction.followup.send(embed=build_embed())

        while wrong <= max_wrong and set(word) - guessed:
            def check(m):
                return (
                    m.author == interaction.user
                    and m.channel == interaction.channel
                    and len(m.content) == 1
                    and m.content.isalpha()
                )

            try:
                reply = await self.bot.wait_for("message", timeout=30, check=check)
            except asyncio.TimeoutError:
                return await interaction.channel.send(embed=error_embed(
                    "Süre Doldu", f"Kelime: **{word}**"))

            letter = reply.content.upper()
            try:
                await reply.delete()
            except discord.Forbidden:
                pass

            if letter in guessed:
                await interaction.channel.send(
                    f"⚠️ `{letter}` harfini zaten denedin!", delete_after=3)
                continue

            guessed.add(letter)

            if letter in word:
                if not set(word) - guessed:
                    await db.update_balance(interaction.user.id, interaction.guild.id, 300)
                    await msg.edit(embed=build_embed())
                    return await interaction.channel.send(embed=success_embed(
                        "Tebrikler! 🎉", f"Kelime: **{word}**\nKazanç: +💰 **300** Altın"))
            else:
                wrong += 1
                if wrong > max_wrong:
                    await msg.edit(embed=build_embed())
                    return await interaction.channel.send(embed=error_embed(
                        "Oyun Bitti! 💀", f"Kelime: **{word}**\nHakkın bitti!"))

            await msg.edit(embed=build_embed())

    # ── SOYGUN ───────────────────────────────────────────────────────────

    @app_commands.command(name="soy", description="Başka birinin parasını çalmaya çalışırsın! (%40 başarı)")
    @app_commands.guild_only()
    @app_commands.describe(üye="Soymaya çalışacağın kullanıcı")
    async def rob(self, interaction: discord.Interaction, üye: discord.Member):
        await interaction.response.defer()

        if üye == interaction.user:
            return await interaction.followup.send(
                embed=error_embed("Kendini soyamazsın!"), ephemeral=True)
        if üye.bot:
            return await interaction.followup.send(
                embed=error_embed("Botları soyamazsın!"), ephemeral=True)

        target_data = await db.get_economy(üye.id, interaction.guild.id)
        if target_data["balance"] < 200:
            return await interaction.followup.send(embed=error_embed(
                "Değmez",
                f"**{üye.display_name}** yeterince parası yok (min. 200 altın)."
            ), ephemeral=True)

        robber_data = await db.get_economy(interaction.user.id, interaction.guild.id)
        fine = 200

        if random.random() < 0.4:
            steal_pct = random.uniform(0.1, 0.3)
            steal_amt = int(target_data["balance"] * steal_pct)
            await db.update_balance(üye.id, interaction.guild.id, -steal_amt)
            await db.update_balance(interaction.user.id, interaction.guild.id, steal_amt)
            embed = success_embed(
                "Soygun Başarılı! 🦹",
                f"**{üye.mention}** kullanıcısından **💰 {format_number(steal_amt)}** altın çaldın!"
            )
        else:
            actual_fine = min(fine, robber_data["balance"])
            await db.update_balance(interaction.user.id, interaction.guild.id, -actual_fine)
            embed = error_embed(
                "Yakalandın! 👮",
                f"Soygun başarısız! Polise 💰 {format_number(actual_fine)} altın ceza ödedi."
            )

        embed.color = Colors.ECONOMY
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
