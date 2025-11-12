import discord
from discord.ext import commands
from discord.ui import Button, View
import os
from dotenv import load_dotenv
from database import RatingDatabase
from datetime import datetime

# Загрузка переменных окружения
load_dotenv()

# Настройка интентов
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True

# Создание бота
bot = commands.Bot(command_prefix='!', intents=intents)
db = RatingDatabase()

@bot.event
async def on_ready():
    print(f'Бот {bot.user} запущен!')
    await bot.change_presence(activity=discord.Game(name="!help для справки"))

@bot.command(name='рейтинг', aliases=['rating', 'р'])
async def show_rating(ctx, member: discord.Member = None):
    """Показать рейтинг пользователя с историей изменений"""
    if member is None:
        member = ctx.author
    
    rating = db.get_rating(member.id)
    history = db.get_rating_history(member.id, limit=5)
    
    embed = discord.Embed(
        title=f"Социальный рейтинг {member.display_name}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Рейтинг", value=f"💎 {rating} **LP**", inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    # Добавляем историю изменений
    if history:
        history_text = ""
        for entry in history:
            try:
                changer = await bot.fetch_user(int(entry['changer_id']))
                changer_name = changer.display_name
            except:
                changer_name = f"Пользователь {entry['changer_id']}"
            
            timestamp = datetime.fromisoformat(entry['timestamp'])
            time_str = timestamp.strftime("%d.%m.%Y %H:%M")
            
            amount_str = f"+{entry['amount']}" if entry['amount'] > 0 else str(entry['amount'])
            comment_str = f" - {entry['comment']}" if entry.get('comment') else ""
            
            history_text += f"**{time_str}** | {amount_str} **LP** от {changer_name}{comment_str}\n"
        
        embed.add_field(
            name="📜 Последние изменения",
            value=history_text if history_text else "История пуста",
            inline=False
        )
    else:
        embed.add_field(
            name="📜 Последние изменения",
            value="История изменений пуста",
            inline=False
        )
    
    await ctx.send(embed=embed)

SONS_ROLE_ID = 1433288795381567579
GRANDFATHERS_ROLE_ID = 1426774131847856161

def family_only():
    async def predicate(ctx):
        user_role_ids = [role.id for role in ctx.author.roles]
        if SONS_ROLE_ID in user_role_ids or GRANDFATHERS_ROLE_ID in user_role_ids:
            return True
        
        await ctx.send("❌ У вас нет доступа! Необходимы роли: `сыновья` или `главные дед`")
        return False
    return commands.check(predicate)

@bot.command(name='добавить', aliases=['add', '+'])
@family_only()
async def add_rating(ctx, amount: int, members: commands.Greedy[discord.Member] = None):
    """Добавить любое количество очков рейтинга (только для модераторов)
    Формат: !добавить количество @user1 @user2 @user3 [комментарий]"""
    # Проверка количества очков
    if amount <= 0:
        await ctx.send("❌ Количество очков должно быть положительным числом!")
        return
    
    # Проверка наличия пользователей
    if not members:
        await ctx.send("❌ Укажите хотя бы одного пользователя!\n"
                      "Формат: `!добавить количество @user1 @user2 [комментарий]`")
        return
    
    # Извлекаем комментарий из оставшегося текста сообщения
    # Используем ctx.message.mentions для более надежного парсинга
    message_content = ctx.message.content
    command_prefix = ctx.prefix
    command_name = ctx.invoked_with
    
    # Удаляем префикс и название команды
    args_text = message_content[len(command_prefix) + len(command_name):].strip()
    
    # Удаляем количество очков (только первое вхождение)
    amount_str = str(amount)
    if args_text.startswith(amount_str):
        args_text = args_text[len(amount_str):].strip()
    elif amount_str in args_text:
        # Если количество не в начале, удаляем первое вхождение
        idx = args_text.find(amount_str)
        # Проверяем, что это отдельное число (окружено пробелами или в начале/конце)
        if idx > 0 and args_text[idx-1] == ' ':
            args_text = args_text[:idx] + args_text[idx+len(amount_str):].strip()
        elif idx == 0:
            args_text = args_text[len(amount_str):].strip()
    
    # Удаляем все упоминания пользователей из текста
    # Используем упоминания из сообщения для точного удаления
    processed_comment = args_text
    for mention in ctx.message.mentions:
        # Удаляем все варианты упоминания
        mention_patterns = [
            f"<@{mention.id}>",
            f"<@!{mention.id}>",
            mention.mention
        ]
        for pattern in mention_patterns:
            processed_comment = processed_comment.replace(pattern, '', 1)
    
    # Очищаем от лишних пробелов
    processed_comment = ' '.join(processed_comment.split()).strip()
    
    # Если комментарий пустой, устанавливаем None
    if not processed_comment:
        processed_comment = None
    
    # Применяем изменения ко всем пользователям
    results = []
    for member in members:
        try:
            old_rating = db.get_rating(member.id)
            new_rating = db.add_rating(member.id, amount, changer_id=ctx.author.id, comment=processed_comment)
            results.append({
                'member': member,
                'old_rating': old_rating,
                'new_rating': new_rating,
                'success': True
            })
        except Exception as e:
            results.append({
                'member': member,
                'error': str(e),
                'success': False
            })
    
    # Создаем embed с результатами
    if len(results) == 1:
        # Один пользователь - используем старый формат для совместимости
        result = results[0]
        if result['success']:
            embed = discord.Embed(
                title="💎 Рейтинг обновлен!",
                description=f"Пользователю {result['member'].mention} добавлено **{amount}** **LP**",
                color=discord.Color.green()
            )
            embed.add_field(name="Было", value=f"💎 {result['old_rating']} **LP**", inline=True)
            embed.add_field(name="Стало", value=f"💎 {result['new_rating']} **LP**", inline=True)
            embed.add_field(name="Изменение", value=f"📈 +{amount} **LP**", inline=True)
            
            if processed_comment:
                embed.add_field(name="💬 Комментарий", value=processed_comment, inline=False)
        else:
            embed = discord.Embed(
                title="❌ Ошибка",
                description=f"Не удалось обновить рейтинг для {result['member'].mention}",
                color=discord.Color.red()
            )
    else:
        # Несколько пользователей - новый формат
        success_count = sum(1 for r in results if r['success'])
        embed = discord.Embed(
            title="💎 Рейтинг обновлен!",
            description=f"Добавлено **{amount}** **LP** для **{success_count}** пользователей",
            color=discord.Color.green()
        )
        
        # Добавляем информацию о каждом пользователе
        users_info = ""
        for result in results:
            if result['success']:
                users_info += f"**{result['member'].display_name}**: {result['old_rating']} → {result['new_rating']} **LP** (+{amount})\n"
            else:
                users_info += f"**{result['member'].display_name}**: ❌ Ошибка\n"
        
        embed.add_field(
            name="📊 Изменения",
            value=users_info if users_info else "Нет изменений",
            inline=False
        )
        
        if processed_comment:
            embed.add_field(name="💬 Комментарий", value=processed_comment, inline=False)
        
        embed.set_footer(text=f"Всего обработано: {len(results)} пользователей")
    
    await ctx.send(embed=embed)

@bot.command(name='убрать', aliases=['remove', '-'])
@family_only()
async def remove_rating(ctx, amount: int, members: commands.Greedy[discord.Member] = None):
    """Убрать любое количество очков рейтинга (только для модераторов)
    Формат: !убрать количество @user1 @user2 @user3 [комментарий]"""
    # Проверка количества очков
    if amount <= 0:
        await ctx.send("❌ Количество очков должно быть положительным числом!")
        return
    
    # Проверка наличия пользователей
    if not members:
        await ctx.send("❌ Укажите хотя бы одного пользователя!\n"
                      "Формат: `!убрать количество @user1 @user2 [комментарий]`")
        return
    
    # Извлекаем комментарий из оставшегося текста сообщения
    # Используем ctx.message.mentions для более надежного парсинга
    message_content = ctx.message.content
    command_prefix = ctx.prefix
    command_name = ctx.invoked_with
    
    # Удаляем префикс и название команды
    args_text = message_content[len(command_prefix) + len(command_name):].strip()
    
    # Удаляем количество очков (только первое вхождение)
    amount_str = str(amount)
    if args_text.startswith(amount_str):
        args_text = args_text[len(amount_str):].strip()
    elif amount_str in args_text:
        # Если количество не в начале, удаляем первое вхождение
        idx = args_text.find(amount_str)
        # Проверяем, что это отдельное число (окружено пробелами или в начале/конце)
        if idx > 0 and args_text[idx-1] == ' ':
            args_text = args_text[:idx] + args_text[idx+len(amount_str):].strip()
        elif idx == 0:
            args_text = args_text[len(amount_str):].strip()
    
    # Удаляем все упоминания пользователей из текста
    # Используем упоминания из сообщения для точного удаления
    processed_comment = args_text
    for mention in ctx.message.mentions:
        # Удаляем все варианты упоминания
        mention_patterns = [
            f"<@{mention.id}>",
            f"<@!{mention.id}>",
            mention.mention
        ]
        for pattern in mention_patterns:
            processed_comment = processed_comment.replace(pattern, '', 1)
    
    # Очищаем от лишних пробелов
    processed_comment = ' '.join(processed_comment.split()).strip()
    
    # Если комментарий пустой, устанавливаем None
    if not processed_comment:
        processed_comment = None
    
    # Применяем изменения ко всем пользователям
    results = []
    for member in members:
        try:
            old_rating = db.get_rating(member.id)
            new_rating = db.remove_rating(member.id, amount, changer_id=ctx.author.id, comment=processed_comment)
            results.append({
                'member': member,
                'old_rating': old_rating,
                'new_rating': new_rating,
                'success': True
            })
        except Exception as e:
            results.append({
                'member': member,
                'error': str(e),
                'success': False
            })
    
    # Создаем embed с результатами
    if len(results) == 1:
        # Один пользователь - используем старый формат для совместимости
        result = results[0]
        if result['success']:
            embed = discord.Embed(
                title="💎 Рейтинг обновлен!",
                description=f"У пользователя {result['member'].mention} убрано **{amount}** **LP**",
                color=discord.Color.orange()
            )
            embed.add_field(name="Было", value=f"💎 {result['old_rating']} **LP**", inline=True)
            embed.add_field(name="Стало", value=f"💎 {result['new_rating']} **LP**", inline=True)
            embed.add_field(name="Изменение", value=f"📉 -{amount} **LP**", inline=True)
            
            if processed_comment:
                embed.add_field(name="💬 Комментарий", value=processed_comment, inline=False)
        else:
            embed = discord.Embed(
                title="❌ Ошибка",
                description=f"Не удалось обновить рейтинг для {result['member'].mention}",
                color=discord.Color.red()
            )
    else:
        # Несколько пользователей - новый формат
        success_count = sum(1 for r in results if r['success'])
        embed = discord.Embed(
            title="💎 Рейтинг обновлен!",
            description=f"Убрано **{amount}** **LP** у **{success_count}** пользователей",
            color=discord.Color.orange()
        )
        
        # Добавляем информацию о каждом пользователе
        users_info = ""
        for result in results:
            if result['success']:
                users_info += f"**{result['member'].display_name}**: {result['old_rating']} → {result['new_rating']} **LP** (-{amount})\n"
            else:
                users_info += f"**{result['member'].display_name}**: ❌ Ошибка\n"
        
        embed.add_field(
            name="📊 Изменения",
            value=users_info if users_info else "Нет изменений",
            inline=False
        )
        
        if processed_comment:
            embed.add_field(name="💬 Комментарий", value=processed_comment, inline=False)
        
        embed.set_footer(text=f"Всего обработано: {len(results)} пользователей")
    
    await ctx.send(embed=embed)

class TopPaginationView(View):
    def __init__(self, bot, all_users, users_per_page=10, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.all_users = all_users
        self.users_per_page = users_per_page
        self.current_page = 0
        self.total_pages = (len(all_users) + users_per_page - 1) // users_per_page if all_users else 1
    
    async def create_embed(self, page):
        """Создать embed для указанной страницы"""
        start_idx = page * self.users_per_page
        end_idx = start_idx + self.users_per_page
        page_users = self.all_users[start_idx:end_idx]
        
        embed = discord.Embed(
            title="🏆 Топ пользователей по **Libero points**",
            color=discord.Color.purple()
        )
        
        if not page_users:
            embed.description = "Пока никто не имеет **LP**!"
            return embed
        
        for i, (user_id, rating) in enumerate(page_users, start=start_idx + 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.display_name
            except:
                username = f"Пользователь {user_id}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(
                name=f"{medal} {username}",
                value=f"💎 {rating}  **LP**",
                inline=False
            )
        
        embed.set_footer(text=f"Страница {page + 1} из {self.total_pages}")
        return embed
    
    @discord.ui.button(label='⬅️', style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
        else:
            self.current_page = self.total_pages - 1
        
        try:
            embed = await self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.defer()
    
    @discord.ui.button(label='➡️', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        else:
            self.current_page = 0
        
        try:
            embed = await self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.defer()
    
    async def on_timeout(self):
        # Отключаем кнопки при истечении времени
        for item in self.children:
            item.disabled = True

@bot.command(name='топ', aliases=['top', 'лидеры'])
async def show_top(ctx, limit: int = None, page: int = None):
    """Показать топ пользователей по рейтингу с пагинацией
    Формат: !топ [лимит] [страница] или !топ [страница]"""
    # Определяем параметры: если первый аргумент <= 20, это лимит, иначе страница
    users_per_page = 10
    current_page = 0
    
    if limit is not None and page is not None:
        # Оба параметра указаны: limit и page
        users_per_page = limit
        current_page = page - 1 if page > 0 else 0
    elif limit is not None:
        if limit <= 20:
            # Это лимит на страницу
            users_per_page = limit
        else:
            # Это номер страницы
            current_page = limit - 1 if limit > 0 else 0
    
    # Ограничения
    if users_per_page > 20:
        users_per_page = 20
    if users_per_page < 1:
        users_per_page = 10
    if current_page < 0:
        current_page = 0
    
    all_users = db.get_all_users_sorted()
    
    if not all_users:
        await ctx.send("Пока никто не имеет **LP**!")
        return
    
    total_pages = (len(all_users) + users_per_page - 1) // users_per_page
    if current_page >= total_pages:
        current_page = total_pages - 1
    
    view = TopPaginationView(ctx.bot, all_users, users_per_page)
    view.current_page = current_page
    
    embed = await view.create_embed(current_page)
    await ctx.send(embed=embed, view=view)

@bot.command(name='мойрейтинг', aliases=['myrating', 'mr'])
async def my_rating(ctx):
    """Показать свой рейтинг"""
    await show_rating(ctx, ctx.author)

@bot.command(name='антитоп', aliases=['antitop', 'днище'])
async def show_bottom(ctx, limit: int = 10):
    """Показать пользователей с наименьшим рейтингом (антитоп)"""
    if limit > 20:
        limit = 20
    if limit < 1:
        limit = 10
    
    bottom_users = db.get_bottom_users(limit)
    
    if not bottom_users:
        await ctx.send("Пока никто не имеет **LP**!")
        return
    
    embed = discord.Embed(
        title="🔻 Антитоп пользователей по **Libero points**",
        color=discord.Color.red()
    )
    
    for i, (user_id, rating) in enumerate(bottom_users, 1):
        try:
            user = await bot.fetch_user(int(user_id))
            username = user.display_name
        except:
            username = f"Пользователь {user_id}"
        
        # Обратная нумерация для антитопа
        position = len(bottom_users) - i + 1
        medal = "🔻" if i == 1 else f"{position}."
        embed.add_field(
            name=f"{medal} {username}",
            value=f"💎 {rating}  **LP**",
            inline=False
        )
    
    await ctx.send(embed=embed)

# Обработка ошибок
@add_rating.error
@remove_rating.error
async def rating_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        command_name = ctx.command.name
        await ctx.send(f"❌ Укажите количество очков и хотя бы одного пользователя!\n"
                      f"Формат: `!{command_name} количество @user1 @user2 [комментарий]`")
    elif isinstance(error, commands.BadArgument):
        command_name = ctx.command.name
        await ctx.send(f"❌ Неверный формат команды!\n"
                      f"Формат: `!{command_name} количество @user1 @user2 [комментарий]`\n"
                      f"Пример: `!{command_name} 10 @user1 @user2 За хорошую работу`")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"❌ Команда на перезарядке! Попробуйте через {error.retry_after:.1f} секунд.")
    else:
        print(f"Ошибка в команде изменения рейтинга: {error}")

@show_rating.error
async def rating_show_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Пользователь не найден!")

@show_bottom.error
async def bottom_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Неверный формат! Используйте: `!антитоп [лимит]`")

@show_top.error
async def top_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Неверный формат! Используйте: `!топ [лимит] [страница]`")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CommandOnCooldown):
        return
    print(f"Ошибка: {error}")

# Запуск бота
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("Ошибка: DISCORD_TOKEN не найден в .env файле")