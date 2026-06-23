from groq import AsyncGroq
from config import GROQ_API_KEY, SYSTEM_PROMPT

client = AsyncGroq(api_key=GROQ_API_KEY)

async def ask_ai(question: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            max_tokens=512,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Hozir javob bera olmayapman, keyinroq urinib ko'ring 😊"
