import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
LEADS_CHAT_ID = int(os.getenv("LEADS_CHAT_ID", "-1001234567890"))

START_TEXT = """😊 Assalomu alaykum!

Mudarris Xalqaro Akademiyasi 0-sinfdan 11-sinfgacha bo'lgan o'quvchilarni qabul qiladi. Akademiyamiz IT, robototexnika, arab tili va ingliz tili yo'nalishlariga ixtisoslashtirilgan.

👨‍🏫 Arab tili darslarini chet ellik malakali ustozlar olib boradilar.

🏆 Farzandingiz akademiyani bitirmasdan turib IELTS, CEFR va SAT kabi sertifikatlardan yuqori ball olish imkoniyatiga ega bo'ladi, chunki bizda ushbu sertifikatlar uchun maxsus tayyorlov guruhlari ham mavjud.

🍽️ Akademiyada kun davomida 4 mahal ovqat beriladi.

✍️ Batafsil ma'lumot olish uchun ro'yxatdan o'ting."""
