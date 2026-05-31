from typing import List, Dict
from urllib.parse import urlparse

from src.tools.web_search import ddg_search_ranked
from src.tools.page_fetch import fetch_html, html_to_text, extract_candidate_lines, extract_email_windows
from src.tools.local_parse import parse_contacts_simple
from src.agents.contact_extractor import extract_contacts_from_text


def normalize_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def run_pipeline(
    query: str,
    company_hint: str,
    domain: str = "",
    region: str = "",
    max_urls: int = 20,
    max_results_search: int = 35,
    llm_fallback: bool = True,
    llm_max_contacts_per_page: int = 25,
) -> List[Dict]:

    results = ddg_search_ranked(query, max_results=max_results_search)
    urls = [r["url"] for r in results if r.get("url")][:max_urls]

    all_contacts: List[Dict] = []


    pages_for_llm: List[Dict] = []


    for url in urls:
        try:
            html = fetch_html(url)
            text = html_to_text(html)

            candidate_short = extract_candidate_lines(text)
            email_windows = extract_email_windows(text, window_lines=8, max_blocks=120)

            local_contacts = parse_contacts_simple(
                candidate_short,
                company=company_hint,
                source_url=url,
            )

            if local_contacts:
                all_contacts.extend(local_contacts)


            pages_for_llm.append({
                "url": url,
                "candidate_short": candidate_short,
                "email_windows": email_windows,
                "text_head": text[:9000],
            })

        except Exception:
            continue


    if llm_fallback:
        for page in pages_for_llm:
            try:
                url = page["url"]
                u_low = url.lower()

                is_managers_like = any(x in u_low for x in [
                    "/sveden/managers", "/managers", "/rukovod", "/management",
                    "/sveden/struct", "/employees", "/staff", "/team", "/persons"
                ])

                if is_managers_like:
                    llm_input = (
                        page["email_windows"]
                        + "\n\n==== PAGE_HEAD ====\n\n"
                        + page["text_head"]
                    ).strip()
                else:
                    llm_input = page["candidate_short"]

                if not llm_input.strip():
                    continue

                llm_contacts = extract_contacts_from_text(
                    text=llm_input,
                    domain=domain or "",
                    region=region or "",
                    max_contacts=llm_max_contacts_per_page,
                )

                for c in llm_contacts:
                    all_contacts.append({
                        "full_name": (c.get("full_name") or "").strip(),
                        "position": (c.get("position") or "").strip(),
                        "email": (c.get("email") or "").strip(),
                        "phone": (c.get("phone") or "").strip(),
                        "source_url": url,
                    })

            except Exception as e:

                print(f"[LLM SKIP] {e}")
                continue


    uniq = {}
    for c in all_contacts:
        email = (c.get("email") or "").lower().strip()
        phone = (c.get("phone") or "").strip()
        source = (c.get("source_url") or "").strip()

        if not source:
            continue
        if not email and not phone:
            continue
        if "example.com" in email:
            continue

        key = email or phone
        if key and key not in uniq:
            uniq[key] = c

    return list(uniq.values())