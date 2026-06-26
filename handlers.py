import re
import logging
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

logger = logging.getLogger(__name__)
router = Router()

class LeadForm(StatesGroup):
    waiting_name = State()
    waiting_phone = State()

class ClearConfirm(StatesGroup):
    waiting_confirm = State()

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Royxatdan otish")]],
        resize_keyboard=True
    )

def is_valid_phone(text: str) -> bool:
    """
    Qabul qilinadigan formatlar:
    - 901234567      (9 ta raqam)
    - 998901234567   (12 ta raqam)
    - +998901234567  (+ bilan 12 ta raqam)
    Boshqa formatlar qabul qilinmaydi.
    """
    digits = re.sub(r'[\s\-\(\)]', '', text)
    # + faqat boshida bo'lishi mumkin
    if digits.startswith('+'):
        digits = digits[1:]
    # Faqat raqamlar qolishi kerak
    if not digits.isdigit():
        return False
    # 9 raqam (masalan 901234567) yoki 12 raqam (998901234567)
    return len(digits) in (9, 12)

def normalize_phone(text: str) -> str:
    digits = re.sub(r'[\s\-\(\)]', '', text)
    if digits.startswith('+'):
        digits = digits[1:]
    if len(digits) == 9:
        return f"+998{digits}"
    return f"+{digits}"

# ===================== /start =====================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await add_user_start(user.id, user.username or "")
    await message.answer(START_TEXT, reply_markup=main_keyboard())

# ===================== Ro'yxatdan o'tish tugmasi =====================
@router.message(F.text == "Royxatdan otish")
async def start_registration(message: Message, state: FSMContext):
    user = message.from_user

    # Avval ro'yxatdan o'tganmi tekshiramiz
    existing = await get_user(user.id)
    if existing and existing[7] == 1:  # is_completed = 1
        await message.answer(
            "Siz allaqachon royxatdan otgansiz!\n\nMutaxassislarimiz tez orada boglanishadi.",
            reply_markup=main_keyboard()
        )
        return

    await state.set_state(LeadForm.waiting_name)
    await message.answer("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())

# ===================== Ism qabul qilish =====================
@router.message(LeadForm.waiting_name)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if not name or name.isdigit():
        await message.answer("Iltimos, ismingizni kiriting:")
        return

    await state.update_data(full_name=name)
    await state.set_state(LeadForm.waiting_phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Kontaktni ulash", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        f"Rahmat, {name}!\n\n"
        "Telefon raqamingizni yuboring.\n"
        "Kontakt tugmasini bosing yoki qolda kiriting:\n"
        "Masalan: 901234567 yoki +998901234567",
        reply_markup=kb
    )

# ===================== Telefon — kontakt tugmasi =====================
@router.message(LeadForm.waiting_phone, F.contact)
async def get_phone_contact(message: Message, state: FSMContext, bot: Bot):
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = f"+{phone}"
    await finish_registration(message, state, bot, phone)

# ===================== Telefon — qo'lda yozish =====================
@router.message(LeadForm.waiting_phone, F.text)
async def get_phone_text(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Kontaktni ulash", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    if not is_valid_phone(raw):
        await message.answer(
            "Notogri raqam. Faqat quyidagi formatda kiriting:\n"
            "901234567  yoki  +998901234567",
            reply_markup=kb
        )
        return

    phone = normalize_phone(raw)
    await finish_registration(message, state, bot, phone)

# ===================== Ro'yxatni yakunlash =====================
async def finish_registration(message: Message, state: FSMContext, bot: Bot, phone: str):
    data = await state.get_data()
    full_name = data.get("full_name")
    user = message.from_user

    await update_user_lead(user.id, full_name, phone)
    await state.clear()

    await message.answer(
        "Muvaffaqiyatli royxatdan otdingiz!\n\nMutaxassislarimiz tez orada boglanishadi. Rahmat!",
        reply_markup=ReplyKeyboardRemove()
    )

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    username_text = f"@{user.username}" if user.username else "Username yoq"

    lead_text = (
        "YANGI LEAD - Mudarris Xalqaro Akademiyasi\n"
        "-----------------------------------\n"
        f"Ism: {full_name}\n"
        f"Telefon: {phone}\n"
        f"Username: {username_text}\n"
        f"Telegram ID: {user.id}\n"
        f"Vaqt: {now}\n"
        "-----------------------------------"
    )

    try:
        await bot.send_message(chat_id=LEADS_CHAT_ID, text=lead_text)
        logger.info(f"Lead yuborildi: {full_name} {phone}")
    except Exception as e:
        logger.error(f"Lead yuborishda xato: {e}")
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"Lead chatga yuborishda xato:\n{e}")
            except:
                pass

# ===================== /stats =====================
@router.message(Command("stats"))
async def show_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Ruxsat yoq.")
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Kunlik"), KeyboardButton(text="Haftalik")],
            [KeyboardButton(text="Oylik"), KeyboardButton(text="Umumiy")]
        ],
        resize_keyboard=True
    )
    await message.answer("Qaysi davrni ko'rishni xohlaysiz?", reply_markup=kb)

@router.message(F.text.in_(["Kunlik", "Haftalik", "Oylik", "Umumiy"]))
async def show_period_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    period_map = {
        "Kunlik": ("day", "Bugun"),
        "Haftalik": ("week", "Sunggi 7 kun"),
        "Oylik": ("month", "Sunggi 30 kun"),
        "Umumiy": ("all", "Barcha vaqt"),
    }

    period_key, period_label = period_map[message.text]
    stats = await get_stats(period_key)

    total = stats["started"]
    completed = stats["completed"]
    not_completed = stats["not_completed"]
    conversion = round((completed / total) * 100, 1) if total > 0 else 0.0

    filled = int(conversion / 10)
    bar = "X" * filled + "." * (10 - filled)

    await message.answer(
        f"Statistika - {period_label}\n"
        "-----------------------------------\n"
        f"Boshlaganlar: {total} ta\n"
        f"Royxatdan otganlar: {completed} ta\n"
        f"Otmaganlar: {not_completed} ta\n"
        "-----------------------------------\n"
        f"Konversiya: {conversion}%\n"
        f"[{bar}]"
    )

# ===================== /leads =====================
@router.message(Command("leads"))
async def show_leads(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Ruxsat yoq.")
        return

    args = message.text.split()
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    per_page = 10
    offset = (page - 1) * per_page

    leads = await get_all_leads(limit=per_page, offset=offset)
    total = await get_leads_count()
    total_pages = max(1, (total + per_page - 1) // per_page)

    if not leads:
        await message.answer("Hozircha lead yoq.")
        return

    lines = [f"Leadlar (sahifa {page}/{total_pages}, jami: {total})\n-----------------------------------"]
    for i, (tg_id, username, full_name, phone, completed_at) in enumerate(leads, start=offset + 1):
        uname = f"@{username}" if username else "-"
        date_str = completed_at[:10] if completed_at else "-"
        lines.append(f"\n{i}. {full_name}\n   Tel: {phone}\n   {uname} | {date_str}")

    if page < total_pages:
        lines.append(f"\nKeyingisi: /leads {page + 1}")

    await message.answer("\n".join(lines))

# ===================== /export =====================
@router.message(Command("export"))
async def export_leads(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Ruxsat yoq.")
        return

    total = await get_leads_count()
    if total == 0:
        await message.answer("Eksport uchun lead yoq.")
        return

    await message.answer("CSV tayyorlanmoqda...")
    csv_bytes = await export_leads_csv()
    filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    await bot.send_document(
        chat_id=message.chat.id,
        document=BufferedInputFile(csv_bytes, filename=filename),
        caption=f"Jami {total} ta lead."
    )

# ===================== /clear_leads =====================
@router.message(Command("clear_leads"))
async def clear_leads_cmd(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Ruxsat yoq.")
        return

    total = await get_leads_count()
    if total == 0:
        await message.answer("Ochirish uchun lead yoq.")
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Ha ochiraman"), KeyboardButton(text="Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await state.set_state(ClearConfirm.waiting_confirm)
    await message.answer(
        f"Diqqat! Bazada {total} ta yozuv bor.\nBarchasini ochirishni tasdiqlaysizmi?\nBu amalni qaytarib bolmaydi!",
        reply_markup=kb
    )

@router.message(ClearConfirm.waiting_confirm, F.text == "Ha ochiraman")
async def confirm_clear(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return
    deleted = await clear_all_leads()
    await state.clear()
    await message.answer(f"{deleted} ta yozuv ochirildi. Baza tozalandi.", reply_markup=ReplyKeyboardRemove())

@router.message(ClearConfirm.waiting_confirm, F.text == "Bekor qilish")
async def cancel_clear(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())

@router.message(ClearConfirm.waiting_confirm)
async def clear_wrong_input(message: Message):
    await message.answer("Iltimos, tugmani bosing.")
