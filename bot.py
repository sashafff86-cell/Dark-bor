import asyncio
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import BOT_TOKEN, CHANNEL_USERNAME, CREATOR_USERNAME
from database import get_user, init_db, update_balance, claim_daily_bonus

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть", callback_data="games")],
        [InlineKeyboardButton(text="💰 Мой Баланс", callback_data="balance"), 
         InlineKeyboardButton(text="🎁 Бонус", callback_data="daily_bonus")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referral")],
        [InlineKeyboardButton(text="📢 Канал", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"),
         InlineKeyboardButton(text="👨‍💻 Связь", url=f"https://t.me/{CREATOR_USERNAME.replace('@', '')}")]
    ])

def get_games_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Монетка", callback_data="game_coin"),
         InlineKeyboardButton(text="🎲 Кости", callback_data="game_dice")],
        [InlineKeyboardButton(text="🎰 Рулетка", callback_data="game_roulette_menu")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])

def get_roulette_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Красное (x2)", callback_data="roulette_red"),
         InlineKeyboardButton(text="⚫ Черное (x2)", callback_data="roulette_black")],
        [InlineKeyboardButton(text="🟢 Зеро (x14)", callback_data="roulette_zero")],
        [InlineKeyboardButton(text="🔙 К играм", callback_data="games")]
    ])

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username or "Игрок"

    referrer_id = None
    if command.args and command.args.isdigit():
        referrer_id = int(command.args)

    await get_user(user_id, username, referrer_id)

    text = (
        f"👑 **Добро пожаловать в GRAM!**\n\n"
        f"GRAM — крутой игровой бот с большим выбором разнообразных игр.\n\n"
        f"🎁 Вам начислен стартовый бонус: **1 000 GRAM**!"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(call: types.CallbackQuery):
    await call.message.edit_text("👑 **Главное меню GRAM**", reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "balance")
async def cb_balance(call: types.CallbackQuery):
    balance = await get_user(call.from_user.id, call.from_user.username)
    await call.answer(f"💰 Ваш баланс: {balance} GRAM", show_alert=True)

@dp.callback_query(F.data == "daily_bonus")
async def cb_daily_bonus(call: types.CallbackQuery):
    success, result = await claim_daily_bonus(call.from_user.id)
    if success:
        await call.answer(f"🎉 Вы получили ежедневный бонус +{result} GRAM!", show_alert=True)
    else:
        hours = result // 3600
        minutes = (result % 3600) // 60
        await call.answer(f"⏳ Следующий бонус можно забрать через {hours} ч. {minutes} мин.", show_alert=True)

@dp.callback_query(F.data == "referral")
async def cb_referral(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={call.from_user.id}"
    text = (
        f"👥 **Реферальная программа**\n\n"
        f"Приглашайте друзей и получайте **+500 GRAM** за каждого нового игрока!\n\n"
        f"🔗 Ваша ссылка:\n`{ref_link}`"
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ]), parse_mode="Markdown")

@dp.callback_query(F.data == "games")
async def cb_games(call: types.CallbackQuery):
    await call.message.edit_text("🎮 **Выберите игру:**", reply_markup=get_games_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "game_roulette_menu")
async def cb_roulette_menu(call: types.CallbackQuery):
    await call.message.edit_text("🎰 **Рулетка**\nСтавка: **200 GRAM**\n\nСделайте ваш выбор:", reply_markup=get_roulette_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("roulette_"))
async def cb_play_roulette(call: types.CallbackQuery):
    choice = call.data.split("_")[1]
    bet = 200
    balance = await get_user(call.from_user.id, call.from_user.username)

    if balance < bet:
        return await call.answer("❌ Недостаточно GRAM (нужно 200)!", show_alert=True)

    spin = random.randint(0, 36)
    if spin == 0:
        result_color = "zero"
        symbol = "🟢 Зеро (0)"
    elif spin % 2 == 0:
        result_color = "red"
        symbol = f"🔴 Красное ({spin})"
    else:
        result_color = "black"
        symbol = f"⚫ Черное ({spin})"

    if choice == result_color:
        multiplier = 14 if choice == "zero" else 2
        win_amount = bet * multiplier
        await update_balance(call.from_user.id, win_amount - bet)
        text = f"🎰 Выпало: {symbol}\n\n🎉 **Победа! Вы выиграли +{win_amount} GRAM!**"
    else:
        await update_balance(call.from_user.id, -bet)
        text = f"🎰 Выпало: {symbol}\n\n😢 **Поражение! Вы потеряли -{bet} GRAM.**"

    await call.message.edit_text(text, reply_markup=get_roulette_keyboard(), parse_mode="Markdown")

async def main():
    await init_db()
    print("Бот GRAM успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
