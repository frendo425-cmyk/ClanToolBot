import asyncio
import datetime
import disnake
from disnake.ext import commands
from disnake.ui import View, Modal, TextInput


# Конфигурация (исправлено: все ID должны быть int)
TARGET_CHANNEL_ID = 1465097766706348075  # ID канала для заявок
ADMIN_ROLE_ID = 1448495553532137543  # ID роли администратора
# Исправлено: добавлены квадратные скобки для списка
CREATE_VOICE_CHANNEL_IDS = [1462838870516174882]  # Триггер-каналы
# Исправлено: добавлены квадратные скобки для списка
TEMP_VOICE_CATEGORY_IDS = [1462840174672220432]  # Категории для голосовых
# Исправлено: добавлены квадратные скобки для списка
WELCOME_ROLE_IDS = [1452023161980846081 ]  # Роли для новых участников

# Список отрядов
SQUADS = [
    "Боевка 1",
    "Боевка 2",
    "Боевка 3",
    "Био",
    "Поддержка",
    "Ралики"
]

bot = commands.Bot(
    command_prefix="!",
    help_command=None,
    intents=disnake.Intents.all(),
    test_guilds=[1448254046749327406, 1459716408953929799]
)

# Хранилище для временных голосовых каналов
bot.temp_channels = {}


class ApplicationModal(Modal):
    """Модальное окно для заявки в отряд"""

    def __init__(self):
        components = [
            TextInput(
                label="Ваш игровой ник",
                placeholder="Например: ShadowHunter",
                custom_id="nickname",
                style=disnake.TextInputStyle.short,
                max_length=50,
                required=True
            ),
            TextInput(
                label="Ваше реальное имя",
                placeholder="Например: Алексей",
                custom_id="real_name",
                style=disnake.TextInputStyle.short,
                max_length=30,
                required=True
            ),
            TextInput(
                label="Ваш K/D (коэффициент убийств/смертей)",
                placeholder="Например: 1.8, 2.3, 3.0",
                custom_id="kd_ratio",
                style=disnake.TextInputStyle.short,
                max_length=10,
                required=True
            ),
            TextInput(
                label="Предпочитаемый отряд",
                placeholder="Выберите из: Боевка 1, Боевка 2, Боевка 3, Био, Поддержка, Ралики",
                custom_id="preferred_squad",
                style=disnake.TextInputStyle.short,
                max_length=30,
                required=True
            ),
            TextInput(
                label="Дополнительная информация",
                placeholder="Расскажите о своем опыте...",
                custom_id="additional_info",
                style=disnake.TextInputStyle.paragraph,
                max_length=400,
                required=False
            )
        ]
        super().__init__(title="📝 Заявка в отряд", components=components, custom_id="application_modal")

    async def callback(self,
                       interaction: disnake.ModalInteraction):  # Исправлено: ModalInteraction вместо MessageInteraction
        nickname = interaction.text_values.get("nickname", "")
        real_name = interaction.text_values.get("real_name", "")
        kd_ratio = interaction.text_values.get("kd_ratio", "")
        preferred_squad = interaction.text_values.get("preferred_squad", "")
        additional_info = interaction.text_values.get("additional_info", "")

        if preferred_squad not in SQUADS:
            await interaction.response.send_message(
                f"❌ Неправильно указан отряд. Выберите из списка:\n{', '.join(SQUADS)}",
                ephemeral=True
            )
            return

        target_channel = bot.get_channel(TARGET_CHANNEL_ID)
        if not target_channel:
            await interaction.response.send_message("❌ Канал для заявок не найден!", ephemeral=True)
            return

        embed = disnake.Embed(
            title="🎖️ НОВАЯ ЗАЯВКА",
            color=disnake.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        user = interaction.author

        # Эмодзи для отрядов
        squad_emojis = {
            "Боевка 1": "⚔️",
            "Боевка 2": "⚔️",
            "Боевка 3": "⚔️",
            "Био": "🦠",
            "Поддержка": "🛡️",
            "Ралики": "🚗"
        }

        squad_emoji = squad_emojis.get(preferred_squad, "🎯")

        embed.add_field(name="🎮 **Игровой ник**", value=f"```{nickname}```", inline=True)
        embed.add_field(name="👤 **Реальное имя**", value=f"```{real_name}```", inline=True)
        embed.add_field(name="⚔️ **K/D**", value=f"```{kd_ratio}```", inline=True)
        embed.add_field(name=f"{squad_emoji} **Отряд**", value=f"```{preferred_squad}```", inline=True)

        if additional_info:
            embed.add_field(
                name="📝 **Дополнительно**",
                value=f"```{additional_info}```",
                inline=False
            )

        embed.add_field(
            name="📱 **Discord информация**",
            value=f"• Пользователь: {user.mention}\n• ID: `{user.id}`\n• На сервере с: <t:{int(user.joined_at.timestamp()) if user.joined_at else 0}:R>",
            inline=False
        )

        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.set_footer(text=f"Заявка #{interaction.id % 10000:04d} • Статус: Ожидание")

        view = AdminDecisionView(user.id)
        message = await target_channel.send(embed=embed, view=view)
        view.message_id = message.id

        # Подтверждение пользователю
        confirm_embed = disnake.Embed(
            title="✅ Заявка отправлена!",
            description="Ваша заявка успешно отправлена на рассмотрение.",
            color=disnake.Color.green()
        )

        confirm_embed.add_field(
            name="📋 Ваши данные",
            value=f"**Ник:** {nickname}\n**Отряд:** {preferred_squad}\n**K/D:** {kd_ratio}",
            inline=False
        )

        confirm_embed.add_field(
            name="🔢 Номер заявки",
            value=f"`#{interaction.id % 10000:04d}`",
            inline=True
        )

        confirm_embed.add_field(
            name="⏱️ Статус",
            value="🔄 На рассмотрении",
            inline=True
        )

        confirm_embed.set_footer(text="С вами свяжутся после решения")

        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        print(f"[ЗАЯВКА] {nickname} → {preferred_squad} (K/D: {kd_ratio})")


class AdminDecisionView(View):
    """Кнопки для администраторов"""

    def __init__(self, applicant_id: int):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.message_id = None

    def is_admin(self, user: disnake.Member) -> bool:
        admin_role = user.guild.get_role(ADMIN_ROLE_ID)
        return admin_role in user.roles or user.guild_permissions.administrator

    @disnake.ui.button(label="✅ Принят", style=disnake.ButtonStyle.green, custom_id="accept_button")
    async def accept_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if not self.is_admin(interaction.author):
            await interaction.response.send_message("❌ Только администраторы могут принимать заявки!", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = disnake.Color.green()
        embed.title = "🎖️ ЗАЯВКА ПРИНЯТА"
        embed.set_footer(
            text=f"{embed.footer.text.split(' • ')[0]} • Статус: ✅ Принят • Админ: {interaction.author.name}")

        new_view = KickView(self.applicant_id, interaction.message.id)
        await interaction.message.edit(embed=embed, view=new_view)

        # Уведомляем игрока
        applicant = interaction.guild.get_member(self.applicant_id)
        if applicant:
            try:
                notify_embed = disnake.Embed(
                    title="🎉 Поздравляем!",
                    description="Ваша заявка в отряд была **ПРИНЯТА**!",
                    color=disnake.Color.green()
                )

                nickname = "Не указан"
                squad = "Не указан"
                for field in embed.fields:
                    if "Игровой ник" in field.name:
                        nickname = field.value.replace("```", "").strip()
                    elif "Отряд" in field.name:
                        squad = field.value.replace("```", "").strip()

                notify_embed.add_field(
                    name="📋 Ваша заявка",
                    value=f"**Ник:** {nickname}\n**Отряд:** {squad}\n**Администратор:** {interaction.author.mention}",
                    inline=False
                )

                notify_embed.add_field(
                    name="📞 Дальнейшие действия",
                    value="С вами скоро свяжется командир отряда.",
                    inline=False
                )

                await applicant.send(embed=notify_embed)
            except:
                pass

        await interaction.response.send_message("✅ Заявка принята!", ephemeral=True)

    @disnake.ui.button(label="❌ Отказ", style=disnake.ButtonStyle.red, custom_id="reject_button")
    async def reject_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if not self.is_admin(interaction.author):
            await interaction.response.send_message("❌ Только администраторы могут отклонять заявки!", ephemeral=True)
            return

        modal = RejectReasonModal(self.applicant_id, interaction.message)
        await interaction.response.send_modal(modal)

    @disnake.ui.button(label="🔄 Обсуждается", style=disnake.ButtonStyle.gray, custom_id="discuss_button")
    async def discuss_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if not self.is_admin(interaction.author):
            await interaction.response.send_message("❌ Только администраторы могут менять статус заявок!",
                                                    ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = disnake.Color.orange()
        embed.title = "🎖️ ЗАЯВКА ОБСУЖДАЕТСЯ"
        embed.set_footer(
            text=f"{embed.footer.text.split(' • ')[0]} • Статус: 🔄 Обсуждается • Админ: {interaction.author.name}")

        await interaction.message.edit(embed=embed)
        await interaction.response.send_message("🔄 Заявка помечена как 'Обсуждается'", ephemeral=True)


class RejectReasonModal(Modal):
    """Причина отказа"""

    def __init__(self, applicant_id: int, message: disnake.Message):
        self.applicant_id = applicant_id
        self.message = message

        components = [
            TextInput(
                label="Укажите причину отказа",
                placeholder="Например: Не соответствует требованиям по K/D...",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
                required=True
            )
        ]
        super().__init__(title="📝 Причина отказа", components=components, custom_id="reject_reason_modal")

    async def callback(self, interaction: disnake.ModalInteraction):  # Исправлено: ModalInteraction
        reason = interaction.text_values.get("reason", "")

        embed = self.message.embeds[0]
        embed.color = disnake.Color.red()
        embed.title = "🎖️ ЗАЯВКА ОТКЛОНЕНА"
        embed.add_field(name="📋 **Причина отказа**", value=f"```{reason}```", inline=False)
        embed.set_footer(
            text=f"{embed.footer.text.split(' • ')[0]} • Статус: ❌ Отклонен • Админ: {interaction.author.name}")

        await self.message.edit(embed=embed, view=None)

        applicant = interaction.guild.get_member(self.applicant_id)
        if applicant:
            try:
                notify_embed = disnake.Embed(
                    title="❌ Заявка отклонена",
                    description="К сожалению, ваша заявка в отряд была отклонена.",
                    color=disnake.Color.red()
                )

                notify_embed.add_field(name="📋 Причина", value=reason, inline=False)
                notify_embed.add_field(name="👤 Администратор", value=interaction.author.mention, inline=True)
                await applicant.send(embed=notify_embed)
            except:
                pass

        await interaction.response.send_message("❌ Заявка отклонена", ephemeral=True)


class KickView(View):
    """Кнопка кика для принятых заявок"""

    def __init__(self, applicant_id: int, message_id: int):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.message_id = message_id

    def is_admin(self, user: disnake.Member) -> bool:
        admin_role = user.guild.get_role(ADMIN_ROLE_ID)
        return admin_role in user.roles or user.guild_permissions.administrator

    @disnake.ui.button(label="👢 Кикнут", style=disnake.ButtonStyle.danger, emoji="👢", custom_id="kick_button")
    async def kick_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if not self.is_admin(interaction.author):
            await interaction.response.send_message("❌ Только администраторы могут кикать игроков!", ephemeral=True)
            return

        modal = KickReasonModal(self.applicant_id, interaction.message)
        await interaction.response.send_modal(modal)


class KickReasonModal(Modal):
    """Причина кика"""

    def __init__(self, applicant_id: int, message: disnake.Message):
        self.applicant_id = applicant_id
        self.message = message

        components = [
            TextInput(
                label="Укажите причину кика",
                placeholder="Например: Нарушение правил, неактивность...",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
                required=True
            )
        ]
        super().__init__(title="👢 Причина кика", components=components, custom_id="kick_reason_modal")

    async def callback(self, interaction: disnake.ModalInteraction):  # Исправлено: ModalInteraction
        reason = interaction.text_values.get("reason", "")

        embed = self.message.embeds[0]
        embed.color = disnake.Color.dark_gray()
        embed.title = "🎖️ ИГРОК КИКНУТ"
        embed.insert_field_at(
            index=len(embed.fields) - 1,
            name="👢 **Причина кика**",
            value=f"```{reason}```",
            inline=False
        )
        embed.set_footer(
            text=f"{embed.footer.text.split(' • ')[0]} • Статус: 👢 Кикнут • Админ: {interaction.author.name}")

        await self.message.edit(embed=embed, view=None)

        applicant = interaction.guild.get_member(self.applicant_id)
        if applicant:
            try:
                kick_embed = disnake.Embed(
                    title="👢 Вас исключили из отряда",
                    description="К сожалению, вы были исключены из отряда.",
                    color=disnake.Color.dark_gray()
                )

                kick_embed.add_field(name="📋 Причина", value=reason, inline=False)
                kick_embed.add_field(name="👤 Администратор", value=interaction.author.mention, inline=True)
                await applicant.send(embed=kick_embed)
            except:
                pass

        await interaction.response.send_message("👢 Игрок кикнут", ephemeral=True)


class ApplicationView(View):
    """Главная кнопка заявки"""

    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="📝 Подать заявку", style=disnake.ButtonStyle.primary, emoji="🎖️", custom_id="apply_button")
    async def apply_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        modal = ApplicationModal()
        await interaction.response.send_modal(modal)


@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов к работе!")
    await bot.change_presence(
        status=disnake.Status.dnd,
        activity=disnake.Game(name="Основные команды: !help")
    )

    # Регистрируем персистентные view
    bot.add_view(ApplicationView())
    bot.add_view(AdminDecisionView(0))
    bot.add_view(KickView(0, 0))


@bot.event
async def on_member_join(member):
    try:
        if member.bot:
            return

        if not member.guild.system_channel:
            print(f"System channel not set for guild: {member.guild.id}")
            return

        # Добавляем все роли из списка
        for role_id in WELCOME_ROLE_IDS:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)

        embed = disnake.Embed(
            title="🎉 Поприветствуйте нового участника!",
            description=f"Добро пожаловать, {member.mention}!\nРады видеть тебя на сервере!",
            color=0xA020F0,
            timestamp=datetime.datetime.now()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Имя пользователя", value=member.name, inline=True)
        embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
        embed.set_footer(text=f"ID: {member.id}")

        await member.guild.system_channel.send(embed=embed)

    except disnake.Forbidden:
        print(f"Missing permissions in guild: {member.guild.id}")
    except Exception as e:
        print(f"Error in on_member_join: {e}")


@bot.event
async def on_voice_state_update(member, before, after):
    """Создание временных голосовых каналов"""
    try:
        # Проверка: пользователь зашел в триггер-канал
        if after.channel and after.channel.id in CREATE_VOICE_CHANNEL_IDS:
            # Проверяем права (исключаем админов/модераторов)
            admin_role = member.guild.get_role(ADMIN_ROLE_ID)

            if admin_role and admin_role in member.roles:
                return

            # Ищем подходящую категорию для гильдии
            category = None
            for category_id in TEMP_VOICE_CATEGORY_IDS:
                cat = member.guild.get_channel(category_id)
                if cat:
                    category = cat
                    break

            if not category:
                print(f"Категория не найдена для ID: {TEMP_VOICE_CATEGORY_IDS}")
                return

            channel_name = f"🎤 {member.name}"

            overwrites = {
                member.guild.default_role: disnake.PermissionOverwrite(
                    view_channel=True,
                    connect=False
                ),
                member: disnake.PermissionOverwrite(
                    connect=True,
                    mute_members=True,
                    deafen_members=True,
                    move_members=True,
                    manage_channels=True,
                    manage_roles=True
                ),
                member.guild.me: disnake.PermissionOverwrite(
                    connect=True,
                    manage_channels=True,
                    manage_roles=True
                )
            }

            new_channel = await category.create_voice_channel(
                name=channel_name,
                overwrites=overwrites,
                user_limit=10,
                bitrate=64000,
                reason=f"Временная комната для {member.name}"
            )

            await member.move_to(new_channel)

            try:
                embed = disnake.Embed(
                    title="🎤 Голосовая комната создана!",
                    description=f"Привет, {member.mention}! Ты создал свою голосовую комнату.",
                    color=0x00FF00
                )

                embed.add_field(
                    name="📋 Доступные команды",
                    value=(
                        "`/name <название>` - изменить название комнаты\n"
                        "`/limit <число>` - установить лимит пользователей\n"
                        "`/invite @пользователь` - пригласить пользователя\n"
                        "`/lock` - закрыть комнату\n"
                        "`/unlock` - открыть комнату"
                    ),
                    inline=False
                )

                embed.set_footer(text="Управляйте своей комнатой с помощью команд!")
                await member.send(embed=embed)
            except:
                pass

            bot.temp_channels[new_channel.id] = {
                "owner": member.id,
                "created_at": datetime.datetime.now(),
                "is_locked": False
            }

        # Проверка: пользователь вышел из голосового канала
        if before.channel and before.channel.id in bot.temp_channels:
            if len(before.channel.members) == 0:
                await asyncio.sleep(60)

                if len(before.channel.members) == 0 and before.channel.id in bot.temp_channels:
                    try:
                        await before.channel.delete(reason="Автоматическое удаление пустой комнаты")
                        del bot.temp_channels[before.channel.id]
                    except Exception as e:
                        print(f"Ошибка при удалении канала: {e}")

    except Exception as e:
        print(f"Error in voice channel creation: {e}")


@bot.event
async def on_message(message: disnake.Message):
    """Обработка скриншотов для заявок"""
    if message.author.bot:
        return

    if message.attachments:
        images = [att for att in message.attachments
                  if any(att.filename.lower().endswith(ext)
                         for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp'])]

        if images:
            target_channel = bot.get_channel(TARGET_CHANNEL_ID)
            if target_channel:
                user_applications = []

                async for msg in target_channel.history(limit=30):
                    if msg.embeds and "ЗАЯВКА" in msg.embeds[0].title:
                        embed = msg.embeds[0]
                        for field in embed.fields:
                            if "ID" in field.name and str(message.author.id) in field.value:
                                user_applications.append((msg, embed))
                                break

                if user_applications:
                    latest_msg, latest_embed = user_applications[0]

                    screenshot_embed = disnake.Embed(
                        title="📸 Скриншот снаряжения",
                        description=f"От {message.author.mention}",
                        color=disnake.Color.green()
                    )

                    screenshot_embed.set_image(url=images[0].url)

                    nickname = "Не указан"
                    for field in latest_embed.fields:
                        if "Игровой ник" in field.name:
                            nickname = field.value.replace("```", "").strip()
                            break

                    screenshot_embed.add_field(
                        name="К заявке",
                        value=f"**Игрок:** {nickname}\n[Заявка #{latest_msg.id % 10000:04d}]({latest_msg.jump_url})",
                        inline=False
                    )

                    await target_channel.send(embed=screenshot_embed)

                    try:
                        await message.delete()
                        await message.channel.send(f"{message.author.mention}, скриншот отправлен в заявку!",
                                                   delete_after=5)
                    except:
                        pass

    await bot.process_commands(message)


# ================ КОМАНДЫ ГЛОСОВЫХ КАНАЛОВ ================

@bot.slash_command(name="name", description="Изменить название голосовой комнаты")
async def voice_name(inter: disnake.ApplicationCommandInteraction, name: str):
    if not inter.author.voice:
        await inter.response.send_message("❌ Вы должны быть в голосовой комнате!", ephemeral=True)
        return

    voice_channel = inter.author.voice.channel

    if voice_channel.id not in bot.temp_channels:
        await inter.response.send_message("❌ Это не временная комната!", ephemeral=True)
        return

    if bot.temp_channels[voice_channel.id]["owner"] != inter.author.id:
        await inter.response.send_message("❌ Вы не являетесь владельцем этой комнаты!", ephemeral=True)
        return

    await voice_channel.edit(name=name[:100])
    await inter.response.send_message(f"✅ Название комнаты изменено на: **{name}**", ephemeral=True)


@bot.slash_command(name="limit", description="Установить лимит пользователей в комнате")
async def voice_limit(inter: disnake.ApplicationCommandInteraction, limit=commands.Range[int, 1, 99]):
    if not inter.author.voice:
        await inter.response.send_message("❌ Вы должны быть в голосовой комнате!", ephemeral=True)
        return

    voice_channel = inter.author.voice.channel

    if voice_channel.id not in bot.temp_channels:
        await inter.response.send_message("❌ Это не временная комната!", ephemeral=True)
        return

    if bot.temp_channels[voice_channel.id]["owner"] != inter.author.id:
        await inter.response.send_message("❌ Вы не являетесь владельцем этой комнаты!", ephemeral=True)
        return

    await voice_channel.edit(user_limit=limit)
    await inter.response.send_message(f"✅ Лимит пользователей установлен: **{limit}**", ephemeral=True)


@bot.slash_command(name="invite", description="Пригласить пользователя в вашу комнату")
async def voice_invite(inter: disnake.ApplicationCommandInteraction, user: disnake.Member):
    if not inter.author.voice:
        await inter.response.send_message("❌ Вы должны быть в голосовой комнате!", ephemeral=True)
        return

    voice_channel = inter.author.voice.channel

    if voice_channel.id not in bot.temp_channels:
        await inter.response.send_message("❌ Это не временная комната!", ephemeral=True)
        return

    if bot.temp_channels[voice_channel.id]["owner"] != inter.author.id:
        await inter.response.send_message("❌ Вы не являетесь владельцем этой комнаты!", ephemeral=True)
        return

    overwrite = disnake.PermissionOverwrite(connect=True)
    await voice_channel.set_permissions(user, overwrite=overwrite)

    await inter.response.send_message(
        f"✅ {user.mention} приглашен в вашу комнату!\n"
        f"Он может подключиться к: {voice_channel.mention}",
        ephemeral=False
    )


@bot.slash_command(name="lock", description="Закрыть комнату от новых подключений")
async def voice_lock(inter: disnake.ApplicationCommandInteraction):
    if not inter.author.voice:
        await inter.response.send_message("❌ Вы должны быть в голосовой комнате!", ephemeral=True)
        return

    voice_channel = inter.author.voice.channel

    if voice_channel.id not in bot.temp_channels:
        await inter.response.send_message("❌ Это не временная комната!", ephemeral=True)
        return

    if bot.temp_channels[voice_channel.id]["owner"] != inter.author.id:
        await inter.response.send_message("❌ Вы не являетесь владельцем этой комнаты!", ephemeral=True)
        return

    overwrite = disnake.PermissionOverwrite(connect=False)
    await voice_channel.set_permissions(inter.guild.default_role, overwrite=overwrite)

    bot.temp_channels[voice_channel.id]["is_locked"] = True
    current_name = voice_channel.name.replace("🔒 ", "")
    await voice_channel.edit(name=f"🔒 {current_name}")
    await inter.response.send_message("✅ Комната закрыта от новых подключений!", ephemeral=True)


@bot.slash_command(name="unlock", description="Открыть комнату для подключений")
async def voice_unlock(inter: disnake.ApplicationCommandInteraction):
    if not inter.author.voice:
        await inter.response.send_message("❌ Вы должны быть в голосовой комнате!", ephemeral=True)
        return

    voice_channel = inter.author.voice.channel

    if voice_channel.id not in bot.temp_channels:
        await inter.response.send_message("❌ Это не временная комната!", ephemeral=True)
        return

    if bot.temp_channels[voice_channel.id]["owner"] != inter.author.id:
        await inter.response.send_message("❌ Вы не являетесь владельцем этой комнаты!", ephemeral=True)
        return

    overwrite = disnake.PermissionOverwrite(connect=True)
    await voice_channel.set_permissions(inter.guild.default_role, overwrite=overwrite)

    bot.temp_channels[voice_channel.id]["is_locked"] = False
    await voice_channel.edit(name=voice_channel.name.replace("🔒 ", ""))
    await inter.response.send_message("✅ Комната открыта для подключений!", ephemeral=True)


# ================ КОМАНДЫ АДМИНИСТРАТИВНЫЕ ================

@bot.command()
async def ping(ctx):
    await ctx.reply(f'Понг! {round(bot.latency * 1000)} мс')


@bot.command(name='clear', help='Удаляет указанное количество сообщений')
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 100):
    await ctx.message.delete()
    deleted_messages = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'Удалено {len(deleted_messages) - 1} сообщений.', delete_after=5)


@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("У вас нет прав для использования этой команды (требуется управление сообщениями).")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Пожалуйста, укажите корректное число сообщений для удаления.")
    else:
        print(f"Произошла ошибка: {error}")


@bot.slash_command(description="Кикнуть пользователя")
@commands.has_permissions(kick_members=True)
async def kick(inter: disnake.ApplicationCommandInteraction, member: disnake.Member, reason: str = "Форзификация"):
    await member.kick(reason=reason)
    await inter.response.send_message(f'✅ {member.mention} был кикнут. Причина: {reason}')


@bot.slash_command(description="Забанить пользователя")
@commands.has_permissions(ban_members=True)
async def ban(inter: disnake.ApplicationCommandInteraction, member: disnake.Member, reason: str = "Форзификация"):
    await member.ban(reason=reason)
    await inter.response.send_message(f'🚫 {member.mention} был забанен. Причина: {reason}')


@kick.error
@ban.error
async def admin_error(inter: disnake.ApplicationCommandInteraction, error):
    if isinstance(error, commands.MissingPermissions):
        await inter.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)


@bot.slash_command(description="Заглушить микрофон пользователя")
@commands.has_permissions(moderate_members=True)
async def mute(
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member,
        minutes: int,
        reason: str = "Много пиздишь!!!"
):
    try:
        await member.edit(mute=True, reason=reason)
        await inter.response.send_message(
            f"✅ Пользователю {member.mention} замучен на {minutes} мин. Причина: {reason}"
        )
        await asyncio.sleep(minutes * 60)
        if member in inter.guild.members:
            await member.edit(mute=False, reason="Срок мута истёк")
    except disnake.Forbidden:
        await inter.response.send_message("❌ У меня нет прав управлять этим пользователем.", ephemeral=True)
    except Exception as e:
        print(f"Ошибка: {e}")


@bot.slash_command(description="Обычный Калькулятор!")
async def calc(inter: disnake.ApplicationCommandInteraction, a: int, oper: str, b: int):
    if oper == "+":
        result = a + b
    elif oper == "-":
        result = a - b
    elif oper == "*":
        result = a * b
    elif oper == "/":
        if b == 0:
            result = "Ошибка: деление на ноль"
        else:
            result = a / b
    else:
        result = "Неверный оператор"
    await inter.send(str(result))


# ================ КОМАНДЫ ДЛЯ СИСТЕМЫ ЗАЯВОК ================

@bot.slash_command(
    name="recruit_panel",
    description="Создает панель для подачи заявок",
    default_member_permissions=disnake.Permissions(manage_messages=True)
)
async def recruit_panel(
        ctx: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = None
):
    await ctx.response.defer(ephemeral=True)

    target = channel or ctx.channel

    main_embed = disnake.Embed(
        title="🎖️ НАБОР В ОТРЯДЫ ОТКРЫТ!",
        description="Присоединяйся к нашим отрядам! Заполни заявку и отправь скриншот снаряжения.",
        color=disnake.Color.dark_gold()
    )

    squad_descriptions = {
        "⚔️ Боевка 1": "Первый боевой отряд",
        "⚔️ Боевка 2": "Второй боевой отряд",
        "⚔️ Боевка 3": "Третий боевой отряд",
        "🦠 Био": "Био отряд",
        "🛡️ Поддержка": "Отряд поддержки",
        "🚗 Ралики": "Отряд гончих"
    }

    squads_text = "\n".join([f"• **{name}** - {desc}" for name, desc in squad_descriptions.items()])
    main_embed.add_field(name="🎯 Доступные отряды", value=squads_text, inline=False)

    main_embed.add_field(
        name="📋 Требования",
        value="""• **K/D 0.5 и выше**
• **Обязательный онлайн на турнирах, потасовки по возможности**
• **Мастерский шмот от +10 до +15**""",
        inline=False
    )

    main_embed.add_field(
        name="📝 Как подать заявку",
        value="1. Нажми кнопку 'Подать заявку'\n2. Заполни все поля формы\n3. Отправь скриншот снаряжения в чат",
        inline=False
    )

    main_embed.set_footer(text="Заявки рассматриваются в течение 24 часов")

    view = ApplicationView()
    await target.send(embed=main_embed, view=view)

    screenshot_embed = disnake.Embed(
        title="📸 Скриншот снаряжения",
        description="**Обязательно отправьте скриншот** после подачи заявки!",
        color=disnake.Color.blue()
    )

    screenshot_embed.add_field(
        name="Что должно быть видно:",
        value="• Весь инвентарь\n• Оружие и моды\n• Броня и шлем\n• Навыки",
        inline=False
    )

    await target.send(embed=screenshot_embed)

    await ctx.edit_original_response(content="✅ Панель создана!")


@bot.slash_command(
    name="review_apps",
    description="Просмотр заявок",
    default_member_permissions=disnake.Permissions(manage_messages=True)
)
async def review_applications(
        ctx: disnake.ApplicationCommandInteraction,
        status: str = commands.Param(
            default="ожидание",
            choices=["все", "ожидание", "принятые", "отклоненные", "кикнутые"]
        )
):
    await ctx.response.defer()

    target_channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not target_channel:
        await ctx.edit_original_response(content="❌ Канал не найден!")
        return

    apps = []
    async for message in target_channel.history(limit=50):
        if message.embeds and "ЗАЯВКА" in message.embeds[0].title:
            apps.append((message, message.embeds[0]))

    if not apps:
        embed = disnake.Embed(title="📭 Заявок нет", color=disnake.Color.green())
        await ctx.edit_original_response(embed=embed)
        return

    filtered_apps = []
    for msg, embed in apps:
        title = embed.title
        if status == "все":
            filtered_apps.append((msg, embed))
        elif status == "ожидание" and "НОВАЯ ЗАЯВКА" in title:
            filtered_apps.append((msg, embed))
        elif status == "принятые" and "ПРИНЯТА" in title:
            filtered_apps.append((msg, embed))
        elif status == "отклоненные" and "ОТКЛОНЕНА" in title:
            filtered_apps.append((msg, embed))
        elif status == "кикнутые" and "КИКНУТ" in title:
            filtered_apps.append((msg, embed))

    embed = disnake.Embed(
        title=f"📋 Заявки ({status})",
        description=f"Найдено: {len(filtered_apps)} из {len(apps)}",
        color=disnake.Color.blue()
    )

    for i, (msg, app_embed) in enumerate(filtered_apps[:10], 1):
        nickname = "Не указан"
        squad = "Не указан"

        for field in app_embed.fields:
            if "Игровой ник" in field.name:
                nickname = field.value.replace("```", "").strip()
            elif "Отряд" in field.name:
                squad = field.value.replace("```", "").strip()

        embed.add_field(
            name=f"{i}. {nickname[:15]}",
            value=f"**Отряд:** {squad}\n[Перейти]({msg.jump_url})",
            inline=False
        )

    await ctx.edit_original_response(embed=embed)


@bot.slash_command(
    name="find_app",
    description="Поиск заявки по нику",
    default_member_permissions=disnake.Permissions(manage_messages=True)
)
async def find_application(
        ctx: disnake.ApplicationCommandInteraction,
        query: str = commands.Param(description="Ник или часть информации для поиска")
):
    await ctx.response.defer()

    target_channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not target_channel:
        await ctx.edit_original_response(content="❌ Канал не найден!")
        return

    found_apps = []
    async for message in target_channel.history(limit=50):
        if message.embeds and "ЗАЯВКА" in message.embeds[0].title:
            embed = message.embeds[0]
            for field in embed.fields:
                if query.lower() in field.value.lower():
                    found_apps.append((message, embed))
                    break

    if not found_apps:
        await ctx.edit_original_response(content=f"❌ Заявки по запросу '{query}' не найдены.")
        return

    embed = disnake.Embed(
        title=f"🔍 Результаты поиска: '{query}'",
        description=f"Найдено: {len(found_apps)}",
        color=disnake.Color.green()
    )

    for i, (msg, app_embed) in enumerate(found_apps[:5], 1):
        nickname = "Не указан"
        for field in app_embed.fields:
            if "Игровой ник" in field.name:
                nickname = field.value.replace("```", "").strip()
                break

        embed.add_field(
            name=f"{i}. {nickname}",
            value=f"[Перейти к заявке]({msg.jump_url})",
            inline=False
        )

    await ctx.edit_original_response(embed=embed)


@bot.slash_command(
    name="help",
    description="Показать все команды бота"
)
async def help_command(inter: disnake.ApplicationCommandInteraction):
    """Показывает список всех доступных команд"""

    embed = disnake.Embed(
        title="📚 Список команд бота",
        description="Все доступные команды разделены по категориям",
        color=disnake.Color.blue()
    )

    # Команды для всех пользователей
    embed.add_field(
        name="👥 **Общие команды**",
        value="""`/calc` - Калькулятор
`/ping` - Проверка пинга
`/help` - Эта справка""",
        inline=False
    )

    # Команды модерации
    if inter.author.guild_permissions.manage_messages:
        embed.add_field(
            name="⚙️ **Команды модерации**",
            value="""`!clear [кол-во]` - Очистка сообщений
`/kick @пользователь [причина]` - Кик пользователя
`/ban @пользователь [причина]` - Бан пользователя
`/mute @пользователь [минуты] [причина]` - Мут пользователя""",
            inline=False
        )

    # Команды голосовых каналов
    embed.add_field(
        name="🎤 **Голосовые комнаты**",
        value="""`/name` - Изменить название комнаты
`/limit` - Установить лимит пользователей
`/invite` - Пригласить пользователя
`/lock` - Закрыть комнату
`/unlock` - Открыть комнату""",
        inline=False
    )

    # Команды системы заявок
    if inter.author.guild_permissions.manage_messages:
        embed.add_field(
            name="🎖️ **Система заявок** (админы)",
            value="""`/recruit_panel` - Создать панель набора
`/review_apps [статус]` - Просмотр заявок
`/find_app [запрос]` - Поиск заявки""",
            inline=False
        )

    embed.add_field(
        name="🎖️ **Система заявок** (игроки)",
        value="Нажмите кнопку 'Подать заявку' на панели набора",
        inline=False
    )

    embed.add_field(
        name="💡 **Как подать заявку?**",
        value="1. Найдите панель набора\n2. Нажмите 'Подать заявку'\n3. Заполните форму\n4. Отправьте скриншот снаряжения",
        inline=False
    )

    embed.set_footer(text=f"Всего команд: {len(bot.slash_commands)}")

    await inter.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    token =("BOT_TOKEN")
    if not token:
        print("❌ Токен бота не найден в переменных окружения!")
        exit(1)
    bot.run(token)
