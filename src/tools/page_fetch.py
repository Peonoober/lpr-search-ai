import re
import httpx
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def fetch_html(url: str, timeout: int = 20) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=timeout) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_candidate_lines(text: str, max_lines: int = 160) -> str:
    keywords = [
        "директор", "генеральный", "руковод", "ceo", "cto", "cmo", "coo",
        "ректор", "проректор", "декан", "заведующий",
        "главный врач", "head", "owner", "founder",
        "правление", "руководство", "команда",
        "контак", "email", "e-mail", "тел", "phone"
    ]

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    good = []
    seen = set()

    for ln in lines:
        low = ln.lower()

        if len(ln) < 18 and ("@" not in ln):
            continue

        if len(ln) > 220:
            continue

        key = low
        if key in seen:
            continue
        seen.add(key)

        looks_like_contact = (
            ("@" in ln) or
            ("+7" in ln) or
            ("8 (" in ln) or
            any(k in low for k in keywords)
        )

        if looks_like_contact:
            good.append(ln)

        if len(good) >= max_lines:
            break

    return "\n".join(good)


def extract_email_windows(text: str, window_lines: int = 7, max_blocks: int = 80) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    email_idxs = [i for i, ln in enumerate(lines) if EMAIL_RE.search(ln or "")]
    blocks = []
    for i in email_idxs[:max_blocks]:
        a = max(0, i - window_lines)
        b = min(len(lines), i + window_lines + 1)
        chunk_lines = [x for x in lines[a:b] if x.strip()]
        chunk = "\n".join(chunk_lines).strip()
        if chunk and chunk not in blocks:
            blocks.append(chunk)
    return "\n\n---\n\n".join(blocks)