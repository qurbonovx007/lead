import re
from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from config import ADMIN_IDS, LEADS_CHAT_ID, START_TEXT
from database import (
    add_user_start, update_user_lead, get_stats, get_user,
    get_all_leads, get_leads_count, clear_all_leads, export_leads_csv
)
from ai import ask_ai

router = Router()

# ===================== STATES =====================
class LeadForm(StatesGroup):
    waiting_name = State()
    waiting_phone = State()

class ClearConfirm(StatesGroup):
    waiting_confirm = State()

# ===================== MAIN KEYBOARD =====================
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✍️ Ro'yxatdan o'tish")]],
        resize_keyboard=True
    )

# ===================== /start =====================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await add_user_start(user.id, user.username or "")

    await message.answer(
        START_TEXT,
        reply_markup=main_keyboard()
    )

# ===================== Ro'yxatdan o'tish =====================
@router.message(F.text == "✍️ Ro'yxatdan o'tish")
async def start_registration(message: Message, state: FSMContext):
    await state.set_state(LeadForm.waiting_name)
    await message.answer(
        "👤 Ismingizni kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )

# ===================== Ism qabul qilish =====================
@router.message(LeadForm.waiting_name)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""

    # Faqat raqam bo'lsa qabul qilmaymiz, lekin 1 harf ham qabul
    if not name or name.isdigit():
        await message.answer("⚠️ Iltimos, ismingizni kiriting:")
        return

    await state.update_data(full_name=name)
    await state.set_state(LeadForm.waiting_phone)

    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Kontaktni ulash", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=contact_keyboard
    )

# ===================== Telefon — kontakt tugmasi orqali =====================
@router.message(LeadForm.waiting_phone, F.contact)
async def get_phone_contact(message: Message, state: FSMContext, bot: Bot):
    phone = message.contact.phone_number
    await finish_registration(message, state, bot, phone)

# ===================== Telefon — qo'lda yozish =====================
@router.message(LeadForm.waiting_phone, F.text)
async def get_phone_text(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip()

    # Harflar bo'lsa qabul qilmaymiz
    if re.search(r'[a-zA-Zа-яА-ЯёЁa-zA-Z]', raw):
        await message.answer(
            "⚠️ Telefon raqamda harf bo'lmasligi kerak. Qaytadan kiriting:"
        )
        return

    # Faqat raqamlar va + qoldiramiz
    phone = re.sub(r'[^\d+]', '', raw)

    if len(phone) < 9:
        await message.answer(
            "⚠️ Noto'g'ri raqam. Qaytadan kiriting:"
        )
        return

    await finish_registration(message, state, bot, phone)

# ===================== Ro'yxatni yakunlash =====================
async def finish_registration(message: Message, state: FSMContext, bot: Bot, phone: str):
    data = await state.get_data()
    full_name = data.get("full_name")
    user = message.from_user

    await update_user_lead(user.id, full_name, phone)
    await state.clear()

    await message.answer(
        "🎉 Rahmat! Mutaxassislarimiz tez orada bog'lanishadi.",
        reply_markup=ReplyKeyboardRemove()
    )

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    username_text = f"@{user.username}" if user.username else "Username yo'q"

    lead_message = (
        "🔔 YANGI LEAD!\n\n"
        f"👤 Ism-Familiya: {full_name}\n"
        f"📞 Telefon: {phone}\n"
        f"🆔 Username: {username_text}\n"
        f"🔗 Telegram ID: {user.id}\n"
        f"🕐 Vaqt: {now}"
    )

    import logging as _log
    _log.getLogger(__name__).info(f"Lead yuborilmoqda: LEADS_CHAT_ID={LEADS_CHAT_ID}")
    try:
        await bot.send_message(chat_id=LEADS_CHAT_ID, text=lead_message)
        _log.getLogger(__name__).info("Lead muvaffaqiyatli yuborildi ✅")
    except Exception as e:
        _log.getLogger(__name__).error(f"Lead yuborishda XATO: {e}")
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"⚠️ Lead chatga yuborishda xato:\n{e}")
            except:
                pass



# ===================== /stats =====================
@router.message(Command("stats"))
async def show_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Ruxsat yo'q.")
        return

    stats_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Kunlik"), KeyboardButton(text="📆 Haftalik")],
            [KeyboardButton(text="🗓 Oylik"), KeyboardButton(text="📊 Umumiy")]
        ],
        resize_keyboard=True
    )
    await message.answer("📊 Qaysi davrni ko'rishni xohlaysiz?", reply_markup=stats_keyboard)

# ===================== Statistika tugmalari =====================
@router.message(F.text.in_(["📅 Kunlik", "📆 Haftalik", "🗓 Oylik", "📊 Umumiy"]))
async def show_period_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    period_map = {
        "📅 Kunlik": ("day", "Bugun"),
        "📆 Haftalik": ("week", "So'nggi 7 kun"),
        "🗓 Oylik": ("month", "So'nggi 30 kun"),
        "📊 Umumiy": ("all", "Barcha vaqt"),
    }

    period_key, period_label = period_map[message.text]
    stats = await get_stats(period_key)

    total = stats["started"]
    completed = stats["completed"]
    not_completed = stats["not_completed"]
    conversion = round((completed / total) * 100, 1) if total > 0 else 0.0

    filled = int(conversion / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    await message.answer(
        f"📊 *Statistika — {period_label}*\n"
        "━━━━━━━━━━━━━━━\n"
        f"👥 Boshlaganlar: *{total}* ta\n"
        f"✅ Ro'yxatdan o'tganlar: *{completed}* ta\n"
        f"❌ O'tmaganlar: *{not_completed}* ta\n"
        "━━━━━━━━━━━━━━━\n"
        f"📈 Konversiya: *{conversion}%*\n"
        f"{bar}",
        parse_mode="Markdown"
    )

# ===================== /leads =====================
@router.message(Command("leads"))
async def show_leads(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Ruxsat yo'q.")
        return

    args = message.text.split()
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    per_page = 10
    offset = (page - 1) * per_page

    leads = await get_all_leads(limit=per_page, offset=offset)
    total = await get_leads_count()
    total_pages = max(1, (total + per_page - 1) // per_page)

    if not leads:
        await message.answer("📭 Hozircha lead yo'q.")
        return

    lines = [f"📋 *Leadlar* (sahifa {page}/{total_pages}, jami: {total})\n━━━━━━━━━━━━━━━"]

    for i, (tg_id, username, full_name, phone, completed_at) in enumerate(leads, start=offset + 1):
        uname = f"@{username}" if username else "—"
        date_str = completed_at[:10] if completed_at else "—"
        lines.append(
            f"\n*{i}.* {full_name}\n"
            f"   📞 `{phone}`\n"
            f"   🆔 {uname} | `{tg_id}`\n"
            f"   📅 {date_str}"
        )

    if total_pages > 1:
        nav = []
        if page > 1:
            nav.append(f"◀️ `/leads {page - 1}`")
        if page < total_pages:
            nav.append(f"`/leads {page + 1}` ▶️")
        lines.append("\n━━━━━━━━━━━━━━━\n" + "   ".join(nav))

    await message.answer("\n".join(lines), parse_mode="Markdown")

# ===================== /export =====================
@router.message(Command("export"))
async def export_leads(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Ruxsat yo'q.")
        return

    total = await get_leads_count()
    if total == 0:
        await message.answer("📭 Eksport uchun lead yo'q.")
        return

    await message.answer("⏳ CSV tayyorlanmoqda...")
    csv_bytes = await export_leads_csv()
    filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    await bot.send_document(
        chat_id=message.chat.id,
        document=BufferedInputFile(csv_bytes, filename=filename),
        caption=f"📊 Jami *{total}* ta lead.",
        parse_mode="Markdown"
    )

# ===================== /clear_leads =====================
@router.message(Command("clear_leads"))
async def clear_leads_cmd(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Ruxsat yo'q.")
        return

    total = await get_leads_count()
    if total == 0:
        await message.answer("📭 O'chirish uchun lead yo'q.")
        return

    confirm_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Ha, o'chiraman"), KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await state.set_state(ClearConfirm.waiting_confirm)
    await message.answer(
        f"⚠️ *Diqqat!*\n\nBazada *{total}* ta yozuv bor.\nBarchasini o'chirishni tasdiqlaysizmi?\n\n_Bu amalni qaytarib bo'lmaydi!_",
        parse_mode="Markdown",
        reply_markup=confirm_keyboard
    )

@router.message(ClearConfirm.waiting_confirm, F.text == "✅ Ha, o'chiraman")
async def confirm_clear(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    deleted = await clear_all_leads()
    await state.clear()
    await message.answer(
        f"🗑 *{deleted}* ta yozuv o'chirildi.\n\nBaza tozalandi ✅",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(ClearConfirm.waiting_confirm, F.text == "❌ Bekor qilish")
async def cancel_clear(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())

@router.message(ClearConfirm.waiting_confirm)
async def clear_wrong_input(message: Message):
    await message.answer("⚠️ Iltimos, tugmani bosing.")

# ===================== AI — har qanday matn (ENG OXIRDA) =====================
BUTTON_TEXTS = [
    "✍️ Ro'yxatdan o'tish",
    "📅 Kunlik", "📆 Haftalik", "🗓 Oylik", "📊 Umumiy",
    "✅ Ha, o'chiraman", "❌ Bekor qilish",
    "📞 Kontaktni ulash",
]

@router.message(F.text & ~F.text.startswith("/"))
async def ai_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return

    if message.text in BUTTON_TEXTS:
        return

    await message.chat.do("typing")
    answer = await ask_ai(message.text)
    await message.answer(answer)
