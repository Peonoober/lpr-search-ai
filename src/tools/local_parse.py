import re
from typing import List, Dict

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+7|8)\s*[\(\-\s]?\d{3}[\)\-\s]?\d{3}[\-\s]?\d{2}[\-\s]?\d{2}")

BAD_POSITION_WORDS = ["контакт", "телефон", "e-mail", "email"]


def _looks_like_email(s: str) -> bool:
    return bool(EMAIL_RE.search(s or ""))


def _looks_like_phone(s: str) -> bool:
    return bool(PHONE_RE.search(s or ""))


def _looks_like_position(s: str) -> bool:
    if not s:
        return False
    low = s.lower()
    if any(w in low for w in BAD_POSITION_WORDS):
        return False
    if _looks_like_email(s):
        return False
    if _looks_like_phone(s):
        return False
    return len(s) >= 8


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

        contacts.append({
            "full_name": "",
            "position": position,
            "company": company,
            "email": email,
            "phone": phone,
            "source_url": source_url
        })

    uniq = {}
    for c in contacts:
        uniq[c["email"]] = c
    return list(uniq.values())