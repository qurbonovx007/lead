import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
LEADS_CHAT_ID = int(os.getenv("LEADS_CHAT_ID", "-1001234567890"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

START_TEXT = """😊 Assalomu alaykum!

Mudarris Xalqaro maktabi 0-sinfdan 11-sinfgacha bo'lgan o'quvchilarni qabul qiladi. Maktabimiz IT, robototexnika, arab tili va ingliz tili yo'nalishlariga ixtisoslashtirilgan.

👨‍🏫 Arab tili darslarini chet ellik malakali ustozlar olib boradilar.

🏆 Farzandingiz maktabni bitirmasdan turib IELTS, CEFR va SAT kabi sertifikatlardan yuqori ball olish imkoniyatiga ega bo'ladi, chunki bizda ushbu sertifikatlar uchun maxsus tayyorlov guruhlari ham mavjud.

🍽️ Maktabda kun davomida 4 mahal ovqat beriladi.

✍️ Batafsil ma'lumot olish uchun ro'yxatdan o'ting."""

SYSTEM_PROMPT = """Sen Mudarris Xalqaro maktabining AI yordamchisisisan. Faqat maktab haqida savollarga javob berasan.

Maktab haqida ma'lumotlar:
- 0-sinfdan 11-sinfgacha qabul qiladi
- IT, robototexnika, arab tili va ingliz tili yo'nalishlariga ixtisoslashgan
- Arab tili darslarini chet ellik malakali ustozlar olib boradi
- O'quvchilar maktabni bitirmasdan IELTS, CEFR va SAT sertifikatlarini olishi mumkin
- Maxsus tayyorlov guruhlari mavjud (IELTS, CEFR, SAT)
- Kun davomida 4 mahal ovqat beriladi
- Maktab nomi: Mudarris Xalqaro maktabi

Qoidalar:
- Faqat maktab haqida savollarga javob ber
- Javoblar qisqa va aniq bo'lsin
- O'zbek tilida javob ber
- Maktab bilan bog'liq bo'lmagan savollarga: "Bu savolga javob bera olmayman, maktab haqida savollaringizni bering 😊" de
- Hech qachon boshqa mavzularga o'tma"""
