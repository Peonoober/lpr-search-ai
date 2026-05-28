import os
import json
from typing import List
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Не падаем, если ключа нет
client = None
if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY)
    except Exception as e:
        print(f"[OPENAI INIT ERROR] {e}")
        client = None


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.replace("```json", "```", 1)
        s = s.strip("`").strip()
    return s


def extract_contacts_from_text(
    text: str,
    domain: str,
    region: str,
    max_contacts: int = 10,
    model_primary: str = "gpt-4o-mini",
    model_fallback: str = "gpt-3.5-turbo"
) -> List[dict]:

    # ✅ Если OpenAI недоступен — просто возвращаем пусто
    if client is None:
        print("[LLM DISABLED] No OpenAI client")
        return []
    print("🔥 OPENAI CALLED")
    system = (
        "Ты — ассистент для извлечения контактов сотрудников/руководства из текста страниц. "
        "Нельзя выдумывать данные. Извлекай только то, что явно написано в тексте. "
        "Нужны именно контакты людей (ФИО + должность), если это возможно. "
        "Не путай телефон с должностью или ФИО. "
        "Если ФИО нет рядом с email — full_name оставь пустым. "
        "Если должности нет — position оставь пустым. "
        "Email example.com игнорируй."
    )

    user = f"""
Контекст:
- Сфера: {domain}
- Регион: {region}

Задача:
Извлеки до {max_contacts} контактов людей из текста.
Связывай ФИО/должность с email/телефоном по ближайшему контексту (в пределах одного блока текста).

Правила:
- Не выдумывай.
- Не включай записи с email содержащим "example.com".
- Если нет source-контекста — не включай.
- Если поля нет — оставь пустую строку.
- full_name — это ФИО человека (если есть в тексте). Не подставляй телефоны и названия подразделений.

Верни строго JSON-массив:
[
  {{
    "full_name": "",
    "position": "",
    "company": "",
    "email": "",
    "phone": ""
  }}
]

Текст:
{text}
""".strip()

    def call(model_name: str) -> str:
        resp = client.chat.completions.create(
            model=model_name,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    try:
        content = call(model_primary)
    except Exception:
        content = call(model_fallback)

    content = _strip_code_fences(content)

    try:
        data = json.loads(content)
        if not isinstance(data, list):
            return []

        cleaned = []
        for item in data:
            if not isinstance(item, dict):
                continue
            email = (item.get("email") or "").strip()
            if "example.com" in email.lower():
                continue
            cleaned.append(item)
        return cleaned
    except Exception:
        return []