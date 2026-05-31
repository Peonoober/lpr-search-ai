import re
from typing import List, Dict

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(\+7|8)\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)

NAME_RE = re.compile(
    r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b"
)


def parse_contacts_simple(
    lines_text: str,
    company: str,
    source_url: str
) -> List[Dict]:

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

        full_name = ""
        for j in range(i - 3, i + 4):
            if 0 <= j < len(lines):
                m = NAME_RE.search(lines[j])
                if m:
                    full_name = m.group(0)
                    break

        contacts.append({
            "full_name": full_name,
            "position": "",
            "email": email,
            "phone": phone,
            "source_url": source_url,
        })

    uniq = {}
    for c in contacts:
        uniq[c["email"]] = c

    return list(uniq.values())