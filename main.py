import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from database import RatingDatabase

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
    """Показать рейтинг пользователя"""
    if member is None:
        member = ctx.author
    
    rating = db.get_rating(member.id)
    
    embed = discord.Embed(
        title=f"Социальный рейтинг {member.display_name}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Рейтинг", value=f"💎 {rating}", inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
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
async def add_rating(ctx, member: discord.Member, amount: int = 1):
    """Добавить любое количество очков рейтинга (только для модераторов)"""
    if amount <= 0:
        await ctx.send("❌ Количество очков должно быть положительным числом!")
        return
    
    old_rating = db.get_rating(member.id)
    new_rating = db.add_rating(member.id, amount)
    
    embed = discord.Embed(
        title="💎 Рейтинг обновлен!",
        description=f"Пользователю {member.mention} добавлено **{amount}** **LP**",
        color=discord.Color.green()
    )
    embed.add_field(name="Было", value=f"💎 {old_rating} **LP**", inline=True)
    embed.add_field(name="Стало", value=f"💎 {new_rating} **LP**", inline=True)
    embed.add_field(name="Изменение", value=f"📈 +{amount} **LP**", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='убрать', aliases=['remove', '-'])
@family_only()
async def remove_rating(ctx, member: discord.Member, amount: int = 1):
    """Убрать любое количество очков рейтинга (только для модераторов)"""
    if amount <= 0:
        await ctx.send("❌ Количество очков должно быть положительным числом!")
        return
    
    old_rating = db.get_rating(member.id)
    new_rating = db.remove_rating(member.id, amount)
    
    embed = discord.Embed(
        title="💎 Рейтинг обновлен!",
        description=f"У пользователя {member.mention} убрано **{amount}**  **LP**",
        color=discord.Color.orange()
    )
    embed.add_field(name="Было", value=f"💎 {old_rating} **LP**", inline=True)
    embed.add_field(name="Стало", value=f"💎 {new_rating} **LP**", inline=True)
    embed.add_field(name="Изменение", value=f"📉 -{amount} **LP**", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='топ', aliases=['top', 'лидеры'])
async def show_top(ctx, limit: int = 10):
    """Показать топ пользователей по рейтингу"""
    if limit > 20:
        limit = 20
    if limit < 1:
        limit = 10
    
    top_users = db.get_top_users(limit)
    
    if not top_users:
        await ctx.send("Пока никто не имеет  **LP**!")
        return
    
    embed = discord.Embed(
        title="🏆 Топ пользователей по **Libero points**",
        color=discord.Color.purple()
    )
    
    for i, (user_id, rating) in enumerate(top_users, 1):
        try:
            user = await bot.fetch_user(int(user_id))
            username = user.display_name
        except:
            username = f"Пользователь {user_id}"
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        embed.add_field(
            name=f"{medal} {username}",
            value=f"💎 {rating}  **LP**",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='мойрейтинг', aliases=['myrating', 'mr'])
async def my_rating(ctx):
    """Показать свой рейтинг"""
    await show_rating(ctx, ctx.author)

# Обработка ошибок
@add_rating.error
@remove_rating.error
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав для использования этой команды!")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Ошибка: {error}")

# Запуск бота
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("Ошибка: DISCORD_TOKEN не найден в .env файле")