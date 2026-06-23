import httpx
from config import GROQ_API_KEY, SYSTEM_PROMPT

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

async def ask_ai(question: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": question}
                    ],
                    "max_tokens": 512,
                    "temperature": 0.5
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"AI xato: {e}")
        return "Hozir javob bera olmayapman, keyinroq urinib ko'ring 😊"
