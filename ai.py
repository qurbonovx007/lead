import httpx
import logging
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "Sen Mudarris Xalqaro maktabining AI yordamchisisisan. "
    "Faqat maktab haqida savollarga javob berasan.\n\n"
    "Maktab haqida malumotlar:\n"
    "- 0-sinfdan 11-sinfgacha qabul qiladi\n"
    "- IT, robototexnika, arab tili va ingliz tili yonalishlariga ixtisoslashgan\n"
    "- Arab tili darslarini chet ellik malakali ustozlar olib boradi\n"
    "- Oquvchilar maktabni bitirmasdan IELTS, CEFR va SAT sertifikatlarini olishi mumkin\n"
    "- Maxsus tayyorlov guruhlari mavjud: IELTS, CEFR, SAT\n"
    "- Kun davomida 4 mahal ovqat beriladi\n"
    "- Maktab nomi: Mudarris Xalqaro maktabi\n\n"
    "Qoidalar:\n"
    "- Faqat maktab haqida savollarga javob ber\n"
    "- Javoblar qisqa va aniq bolsin\n"
    "- Uzbek tilida javob ber\n"
    "- Maktab bilan boglik bolmagan savollarga: Bu savolga javob bera olmayman, maktab haqida savollaringizni bering de\n"
    "- Hech qachon boshqa mavzularga otma"
)

async def ask_ai(question: str) -> str:
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY bosh!")
        return "AI sozlanmagan."

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": question}
                    ],
                    "max_tokens": 512,
                    "temperature": 0.5
                }
            )

            if response.status_code != 200:
                logger.error(f"Groq {response.status_code}: {response.text}")
                return "Hozir javob bera olmayapman, keyinroq urinib ko'ring 😊"

            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"AI exception: {type(e).__name__}: {e}")
        return "Hozir javob bera olmayapman, keyinroq urinib ko'ring 😊"
