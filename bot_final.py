import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ============================================================
#  НАЛАШТУВАННЯ — замінити перед запуском
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8665613428:AAHekxEplW7YAvh_y4t9KJ_anWwOttkPvPg")
ADMIN_USERNAME = "Valdema6"          # без @
ADMIN_CHAT_ID = None                 # заповниться автоматично при першому /start адміна
ADMIN_USERNAMES = {"Valdema6", "rolermusic", "gggftke"}
GROUP_CHAT_ID = None
pending_questions: dict = {}

# ============================================================
#  КОНТЕНТ КЛУБУ
# ============================================================
CLUB_NAME = "Intelligent Kids"

ABOUT_CLUB = """🥋 *Клуб Brazilian Jiu-Jitsu — Intelligent Kids*

Ми навчаємо дітей та дорослих техніці BJJ в дружній та безпечній атмосфері.

Наші цінності:
• Дисципліна та повага
• Постійний прогрес
• Командний дух
• Безпечне тренування

Приєднуйся до нашої сім'ї! 💪"""

ABOUT_TRAINER = """👨‍🏫 *Тренер — Паламарчук Володимир*

🎽 Пояс: Синій (Blue Belt)
⏱ Досвід: 3,5 роки

🏆 *Турнірні досягнення:*

🌍 *Міжнародні:*
• 🥈 European IBJJF Jiu-Jitsu Championship 2026
  Adult / White / Light -76kg

🇺🇦 *Національні та всеукраїнські:*
• 🥇 TMS Challenge Cup 2026 — Adult GI / Blue / 76kg
• 🥇 TMS Ukrainian Championship — Adult GI / White / 82.3kg
• 🥇 TMS Victory Cup 2025 — Juvenile No-Gi / White / 76.5kg
• 🥈 TMS Victory Cup 2025 — Absolute No-Gi / Juvenile
• 🥇 TMS Ukrainian Cup + Grand Prix Final 2024 — *(фінал)*
• 🥈 TMS Ukrainian Cup + Grand Prix Final 2024 — Juvenile No-Gi / White / 71.5kg
• 🥉 TMS Ukrainian Cup 2024 — Juvenile No-Gi / White / 71.5kg
• 🥇 TMS Ukrainian Championship 2023 Kyiv — Teen No-Gi / White / 68+kg
• 🥇 TMS Ukrainian Championship 2023 Kyiv — Teen GI / White / 69+kg
• 🥈 TMS Ukrainian Cup 2023 Kyiv — Teen GI / White / 69+kg

🎯 *Sub Only турніри:*
• 🥇 Sub Only - Submission Force — Adult / Novice / 80kg
• 🥇 Sub Only - Submission Force — Absolute / Adult / Novice
• 🥇 Sub Only Championship Autumn Cup — Juvenile (16-17) / 75kg
• 🥇 Sub Only Championship Spring Cup Kyiv — Juvenile (16-17) / 70+kg
• 🥉 Sub Only Championship Spring Cup Kyiv — Juvenile Absolute (16-17)
• 🥇 Sub Only Championship Winter Cup Kyiv — Juvenile (16-17) / 70+kg
• 🥇 Sub Only Championship Winter Cup Kyiv — Juvenile Absolute (16-17)
• 🥇 Sub Only Ukrainian Championship — Juvenile (16-17) / Novice / 70kg

🎽 *TMS Prime Cup 2025:*
• 🥇 Juvenile No-Gi / White / 71.5kg
• 🥈 Juvenile GI / White / 74kg

🔗 Повний профіль: https://lpjj.smoothcomp.com/ua/profile/1077972

Треную з душею та відповідальністю. Мета — дати кожному учню якісну техніку та впевненість на килимку 💪"""

SCHEDULE = """🗓 *Розклад тренувань*

📅 *Понеділок* — 16:30 – 18:00
📅 *Середа* — 16:30 – 18:00
📅 *П'ятниця* — 16:30 – 18:00

Тривалість: 1.5 год
Рівень: всі рівні вітаються 🤍"""

PRICES = """💰 *Вартість тренувань*

┌────────────────────────────┐
│  Разове тренування         │
│  💵 400 грн                │
├────────────────────────────┤
│  Абонемент на місяць       │
│  📆 12 тренувань           │
│  💵 2 500 грн              │
│  (економія 300 грн)        │
├────────────────────────────┤
│  Індивідуальне заняття     │
│  👤 1 на 1 з тренером      │
│  💵 800 грн                │
└────────────────────────────┘

💬 Для оплати або питань — пишіть тренеру: @Valdema6"""

# ============================================================
#  БД
# ============================================================
def init_db():
    conn = sqlite3.connect("club.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            experience TEXT,
            registered_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_member(tg_id, username, full_name, phone, experience):
    conn = sqlite3.connect("club.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO members (tg_id, username, full_name, phone, experience, registered_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (tg_id, username, full_name, phone, experience, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_members():
    conn = sqlite3.connect("club.db")
    c = conn.cursor()
    c.execute("SELECT full_name, phone, experience, username, registered_at FROM members ORDER BY registered_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def is_registered(tg_id):
    conn = sqlite3.connect("club.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM members WHERE tg_id=?", (tg_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

# ============================================================
#  FSM — реєстрація
# ============================================================
class Registration(StatesGroup):
    full_name  = State()
    phone      = State()
    experience = State()

class Question(StatesGroup):
    waiting = State()

# ============================================================
#  КЛАВІАТУРИ
# ============================================================
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Реєстрація"), KeyboardButton(text="🗓 Розклад")],
            [KeyboardButton(text="💰 Абонементи"), KeyboardButton(text="📢 Новини")],
            [KeyboardButton(text="👨‍🏫 Тренер"),    KeyboardButton(text="ℹ️ Про клуб")],
            [KeyboardButton(text="📍 Локація"),     KeyboardButton(text="❓ Запитання")],
        ],
        resize_keyboard=True
    )

def experience_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 Новачок (немає досвіду)")],
            [KeyboardButton(text="📗 Є трохи досвіду (до 1 року)")],
            [KeyboardButton(text="📘 Досвідчений (1–3 роки)")],
            [KeyboardButton(text="📕 Просунутий (3+ роки)")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True
    )

# ============================================================
#  БОТ
# ============================================================
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
logger = logging.getLogger(__name__)

# ---- /start ------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    global ADMIN_CHAT_ID
    if message.from_user.username == ADMIN_USERNAME:
        ADMIN_CHAT_ID = message.chat.id
    await message.answer(
        f"👋 Вітаємо в клубі *{CLUB_NAME}*!\n\n"
        "Оберіть розділ у меню нижче 👇",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ---- Про клуб ---------------------------------------------
@dp.message(F.text == "ℹ️ Про клуб")
async def about_club(message: types.Message):
    await message.answer(ABOUT_CLUB, parse_mode="Markdown", reply_markup=main_menu())

# ---- Тренер -----------------------------------------------
@dp.message(F.text == "👨‍🏫 Тренер")
async def about_trainer(message: types.Message):
    await message.answer(ABOUT_TRAINER, parse_mode="Markdown", reply_markup=main_menu())

# ---- Розклад ----------------------------------------------
@dp.message(F.text == "🗓 Розклад")
async def schedule(message: types.Message):
    await message.answer(SCHEDULE, parse_mode="Markdown", reply_markup=main_menu())

# ---- Ціни -------------------------------------------------
@dp.message(F.text == "💰 Абонементи")
async def prices(message: types.Message):
    await message.answer(PRICES, parse_mode="Markdown", reply_markup=main_menu())

# ---- Локація ----------------------------------------------
@dp.message(F.text == "📍 Локація")
async def location(message: types.Message):
    await message.answer(
        "📍 *Наше розташування*\n\n"
        "Натисни на посилання щоб відкрити в Google Maps:\n"
        "https://maps.app.goo.gl/KNeAEJq2P5Jwh4hv8",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


@dp.message(F.text == "📢 Новини")
async def news(message: types.Message):
    await message.answer(
        "📢 *Новини клубу*\n\n"
        "Наразі нових оголошень немає.\n"
        "Слідкуй за оновленнями! 💪",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ---- Реєстрація — старт -----------------------------------
@dp.message(F.text == "📋 Реєстрація")
async def reg_start(message: types.Message, state: FSMContext):
    if is_registered(message.from_user.id):
        await message.answer(
            "✅ Ти вже зареєстрований!\n\n"
            "Якщо хочеш оновити дані — напиши тренеру: @Valdema6",
            reply_markup=main_menu()
        )
        return
    await state.set_state(Registration.full_name)
    await message.answer(
        "📋 *Реєстрація нового учасника*\n\n"
        "Крок 1/3 — Введи своє *ім'я та прізвище*:",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )

@dp.message(Registration.full_name)
async def reg_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Реєстрацію скасовано.", reply_markup=main_menu())
        return
    await state.update_data(full_name=message.text)
    await state.set_state(Registration.phone)
    await message.answer(
        "Крок 2/3 — Введи свій *номер телефону* (або натисни кнопку нижче):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Поділитись номером", request_contact=True)],
                [KeyboardButton(text="❌ Скасувати")]
            ],
            resize_keyboard=True
        )
    )

@dp.message(Registration.phone, F.contact)
async def reg_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await state.set_state(Registration.experience)
    await message.answer(
        "Крок 3/3 — Який у тебе рівень досвіду в BJJ?",
        reply_markup=experience_kb()
    )

@dp.message(Registration.phone)
async def reg_phone_text(message: types.Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Реєстрацію скасовано.", reply_markup=main_menu())
        return
    await state.update_data(phone=message.text)
    await state.set_state(Registration.experience)
    await message.answer(
        "Крок 3/3 — Який у тебе рівень досвіду в BJJ?",
        reply_markup=experience_kb()
    )

@dp.message(Registration.experience)
async def reg_experience(message: types.Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Реєстрацію скасовано.", reply_markup=main_menu())
        return
    data = await state.get_data()
    save_member(
        tg_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=data["full_name"],
        phone=data["phone"],
        experience=message.text
    )
    await state.clear()

    # Повідомлення учаснику
    await message.answer(
        f"✅ *Реєстрація успішна!*\n\n"
        f"👤 Ім'я: {data['full_name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🥋 Рівень: {message.text}\n\n"
        f"Тренер зв'яжеться з тобою найближчим часом.\n"
        f"Або напиши сам: @Valdema6 💪",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

    # Повідомлення адміну
    if ADMIN_CHAT_ID:
        username_str = f"@{message.from_user.username}" if message.from_user.username else "немає"
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🔔 *Нова реєстрація!*\n\n"
            f"👤 {data['full_name']}\n"
            f"📱 {data['phone']}\n"
            f"🥋 {message.text}\n"
            f"💬 TG: {username_str}",
            parse_mode="Markdown"
        )

# ---- Адмін: /members --------------------------------------
@dp.message(Command("members"))
async def cmd_members(message: types.Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    members = get_all_members()
    if not members:
        await message.answer("Поки немає зареєстрованих учасників.")
        return
    text = f"👥 *Зареєстровані учасники ({len(members)}):*\n\n"
    for i, (name, phone, exp, username, reg_at) in enumerate(members, 1):
        uname = f"@{username}" if username else "—"
        date  = reg_at[:10] if reg_at else "—"
        text += f"{i}. *{name}*\n   📱 {phone} | {uname}\n   🥋 {exp}\n   📅 {date}\n\n"
    await message.answer(text, parse_mode="Markdown")

# ---- Адмін: /news <текст> ---------------------------------
@dp.message(Command("news"))
async def cmd_news(message: types.Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    text = message.text.replace("/news", "").strip()
    if not text:
        await message.answer("Використання: /news Текст оголошення")
        return
    members_rows = get_all_members()
    conn = sqlite3.connect("club.db")
    c = conn.cursor()
    c.execute("SELECT tg_id FROM members")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    sent = 0
    for tg_id in ids:
        try:
            await bot.send_message(tg_id, f"📢 *Оголошення від клубу {CLUB_NAME}:*\n\n{text}", parse_mode="Markdown")
            sent += 1
        except Exception:
            pass
    await message.answer(f"✅ Розіслано {sent}/{len(ids)} учасникам.")

# ---- Адмін: /help -----------------------------------------
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    await message.answer(
        "🛠 *Адмін-команди:*\n\n"
        "/members — список зареєстрованих учасників\n"
        "/news Текст — розіслати оголошення всім учасникам",
        parse_mode="Markdown"
    )

# ============================================================
# ---- /getid — для групового чату ---------------------------
@dp.message(Command("getid"))
async def cmd_getid(message: types.Message):
    global GROUP_CHAT_ID
    if message.chat.type in ("group", "supergroup"):
        GROUP_CHAT_ID = message.chat.id
        await message.answer(f"✅ ID групи збережено: `{GROUP_CHAT_ID}`", parse_mode="Markdown")
    else:
        await message.answer(f"Твій chat_id: `{message.chat.id}`", parse_mode="Markdown")

# ---- Запитання — старт ------------------------------------
@dp.message(F.text == "❓ Запитання")
async def question_start(message: types.Message, state: FSMContext):
    await state.set_state(Question.waiting)
    await message.answer(
        "❓ *Задай своє запитання*\n\n"
        "Напиши текст і ми відповімо якнайшвидше 👇",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )

@dp.message(Question.waiting)
async def question_receive(message: types.Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return

    await state.clear()
    await message.answer(
        "✅ Запитання надіслано! Відповімо найближчим часом 💬",
        reply_markup=main_menu()
    )

    if GROUP_CHAT_ID:
        username_str = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        sent = await bot.send_message(
            GROUP_CHAT_ID,
            f"❓ *Запитання від {username_str}*\n\n{message.text}\n\n"
            f"_Відповідай через Reply на це повідомлення_",
            parse_mode="Markdown"
        )
        pending_questions[sent.message_id] = message.from_user.id

# ---- Відповідь адміна через Reply в групі -----------------
@dp.message(F.chat.type.in_({"group", "supergroup"}), F.reply_to_message)
async def group_reply(message: types.Message):
    if message.from_user.username not in ADMIN_USERNAMES:
        return
    replied_id = message.reply_to_message.message_id
    user_id = pending_questions.get(replied_id)
    if not user_id:
        return
    try:
        await bot.send_message(
            user_id,
            f"💬 *Відповідь від тренера:*\n\n{message.text}",
            parse_mode="Markdown"
        )
        await message.react([types.ReactionTypeEmoji(emoji="✅")])
    except Exception:
        await message.answer("❌ Не вдалось надіслати відповідь користувачу.")

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
