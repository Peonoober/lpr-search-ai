import re
from typing import List, Dict

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(\+7|8)\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)

BAD_POSITION_WORDS = ["контакт", "телефон", "e-mail", "email"]


def _looks_like_email(s: str) -> bool:
    return bool(EMAIL_RE.search(s or ""))


def _looks_like_phone(s: str) -> bool:
    return bool(PHONE_RE.search(s or ""))


def _looks_like_position(s: str) -> bool:
    if not s:
        return False

    low = s.lower()


    if _looks_like_email(s):
        return False


    if _looks_like_phone(s):
        return False


    digits = sum(c.isdigit() for c in s)
    if digits > 4:
        return False


    keywords = [
        "директор", "генераль", "руковод", "ректор",
        "проректор", "декан", "глав", "начальник",
        "head", "ceo", "cto", "cmo"
    ]

    if any(k in low for k in keywords):
        return True


    return len(s) > 10

NAME_RE = re.compile(r"[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}")
def parse_contacts_simple(lines_text: str, company: str, source_url: str) -> List[Dict]:
    lines = [ln.strip() for ln in lines_text.splitlines() if ln.strip()]
    contacts: List[Dict] = []

    for i, ln in enumerate(lines):
        emails = EMAIL_RE.findall(ln)
        if not emails:
            continue

        email = emails[0]

        phone = ""
        for j in range(max(0, i - 3), min(len(lines), i + 4)):
            m = PHONE_RE.search(lines[j])
            if m:
                phone = m.group(0)
                break

        position = ""
        for j in range(i - 3, i + 4):
            if 0 <= j < len(lines) and _looks_like_position(lines[j]):
                position = lines[j]
                break

        full_name = ""
        for j in range(i - 3, i + 4):
            if 0 <= j < len(lines):
                m = NAME_RE.search(lines[j])
                if m:
                    full_name = m.group(0)
                    break

        contacts.append({
            "full_name": full_name,
            "position": position,
            "email": email,
            "phone": phone,
            "source_url": source_url,
        })

    uniq = {}
    for c in contacts:
        uniq[c["email"]] = c
    return list(uniq.values())