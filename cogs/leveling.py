@commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Her mesajda XP kazandırır.
        """
        # Bot kendi mesajlarını okumasın ve DM'leri geç
        if message.author.bot or not message.guild:
            return

        # Komutları yoksay (prefix ile başlıyorsa XP verme)
        # Prefix'in ne olduğunu tahmin etmeye çalışma, direkt '!' kontrolü yapalım
        if message.content.startswith("!"):
            return

        user_id  = message.author.id
        guild_id = message.guild.id
        now      = datetime.datetime.utcnow().timestamp()

        # Cooldown kontrolü (60 saniye)
        key = f"{user_id}:{guild_id}"
        if key in self._xp_cooldowns:
            if now - self._xp_cooldowns[key] < 60:
                return

        self._xp_cooldowns[key] = now

        # Rastgele XP ver
        import random
        xp = random.randint(*self.XP_PER_MESSAGE)
        result = await db.add_xp(user_id, guild_id, xp)

        # Seviye atlandıysa kutla
        if result["leveled_up"]:
            new_level = result["new_level"]
            embed = discord.Embed(
                title="🎉 Seviye Atlandı!",
                description=(
                    f"Tebrikler {message.author.mention}!\n"
                    f"**Seviye {new_level - 1}** → **Seviye {new_level}** 🚀"
                ),
                color=Colors.LEVEL,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)

            # Seviye ödülü
            reward = new_level * 100
            await db.update_balance(user_id, guild_id, reward)
            embed.add_field(
                name="🎁 Seviye Ödülü",
                value=f"+💰 **{format_number(reward)}** Altın"
            )

            try:
                lvl_msg = await message.channel.send(embed=embed)
                await asyncio.sleep(10)
                await lvl_msg.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
