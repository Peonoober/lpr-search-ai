from ddgs import DDGS

BAD_DOMAIN_PARTS = [
    "hh.ru/vacancies",
    "rabota.", "superjob.", "job", "vacancy"
]


def _is_bad(url: str) -> bool:
    u = (url or "").lower()

    if any(p in u for p in BAD_DOMAIN_PARTS):
        return True

    return False


def ddg_search_ranked(query: str, max_results: int = 10) -> list[dict]:
    raw = []

    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            title = r.get("title", "")
            url = r.get("href", "")
            snippet = r.get("body", "")

            if not url:
                continue

            if _is_bad(url):
                continue

            raw.append({
                "title": title,
                "url": url,
                "snippet": snippet,
            })

    uniq = {}
    for item in raw:
        uniq[item["url"]] = item

    return list(uniq.values())