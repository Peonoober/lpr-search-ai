from ddgs import DDGS

BAD_DOMAIN_PARTS = [
    "hh.ru/vacancies",
    "rabota.", "superjob.", "job", "vacancy"
]

BAD_WORDS = [
    "автосервис", "шиномонтаж", "ремонт", "сто ", "техобслуживание", "запчаст"
]


def _is_bad(url: str, snippet: str) -> bool:
    u = (url or "").lower()
    s = (snippet or "").lower()

    if any(p in u for p in BAD_DOMAIN_PARTS):
        return True

    if any(w in s for w in BAD_WORDS) or any(w in u for w in BAD_WORDS):
        return True

    return False


def _score(title: str, snippet: str, url: str) -> int:
    t = (title or "").lower()
    s = (snippet or "").lower()
    u = (url or "").lower()

    score = 0

    # плюс за "контактные" страницы
    if any(x in u for x in ["/contacts", "/contact", "/team", "/management", "/about", "/rukovodstvo", "/persons"]):
        score += 3

    # плюс за указания на руководителей/команду
    if any(x in s for x in ["руковод", "правление", "команда", "директор", "генеральный", "cto", "ceo", "cmo", "head", "leadership", "management"]):
        score += 2

    # плюс за наличие email прямо в сниппете
    if "@" in s:
        score += 2

    # небольшой плюс, если в заголовке есть "контакты/команда"
    if any(x in t for x in ["контак", "команд", "руковод", "leadership", "team"]):
        score += 1

    return score


def ddg_search_ranked(query: str, max_results: int = 10) -> list[dict]:
    """
    Возвращает ранжированные результаты DDG:
    [{title,url,snippet,score}]
    """
    raw = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            title = r.get("title", "")
            url = r.get("href", "")
            snippet = r.get("body", "")

            if not url:
                continue
            if _is_bad(url, snippet):
                continue

            raw.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "score": _score(title, snippet, url)
            })

    # дедуп по url
    uniq = {}
    for item in raw:
        uniq[item["url"]] = item

    results = list(uniq.values())
    results.sort(key=lambda x: x["score"], reverse=True)
    return results