import os
import re
from typing import Any, Dict, List

import firebase_admin
from firebase_admin import credentials, firestore

from src.services.pipeline import run_pipeline

PHONE_RE = re.compile(r"(\+7|8)\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")


def _get_db() -> firestore.Client:
    if not firebase_admin._apps:
        json_path = "/etc/secrets/firebase-admin-sdk.json"

        if not os.path.exists(json_path):
            raise FileNotFoundError(
                f"Service account key not found at {json_path}"
            )

        cred = credentials.Certificate(json_path)
        firebase_admin.initialize_app(cred)

    return firestore.client()


def _build_search_query(order_data: Dict[str, Any]) -> str:
    criteria = order_data.get("searchCriteria") or {}

    industry = (criteria.get("industry") or "").strip()
    region = (criteria.get("region") or "").strip()
    details = (criteria.get("details") or "").strip()

    parts: List[str] = []

    if details:
        parts.append(details)

    if industry:
        parts.append(industry)

    if region:
        parts.append(region)

    parts.append(
        '(site:.ru OR site:.edu OR site:.ac.ru) '
        '(руководство OR ректорат OR ректор OR проректор OR декан) '
        '(email OR контакты)'
    )

    return " ".join(parts)


def _dedup_contacts(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    uniq: Dict[str, Dict[str, Any]] = {}

    for c in items:
        email = (c.get("email") or "").lower().strip()
        phone = (c.get("phone") or "").strip()
        source = (c.get("source_url") or "").strip()

        if not source:
            continue

        if not email and not phone:
            continue

        bad_prefixes = ["info@", "hello@", "support@", "admin@", "office@", "contact@"]
        if any(email.startswith(p) for p in bad_prefixes):
            continue

        key = email or phone

        if key and key not in uniq:
            uniq[key] = c

    return list(uniq.values())


def start_lpr_search(order_id: str):
    print(f"\n[START] Order {order_id}")

    db = _get_db()
    order_ref = db.collection("orders").document(order_id)

    snap = order_ref.get()

    if not snap.exists:
        print(f"[ERROR] Order {order_id} not found")
        return

    order_data: Dict[str, Any] = snap.to_dict() or {}
    criteria = order_data.get("searchCriteria") or {}

    company_hint = (criteria.get("company") or "").strip()
    industry = (criteria.get("industry") or "").strip()
    region = (criteria.get("region") or "").strip()

    order_ref.update({"status": "Поиск"})

    base_query = _build_search_query(order_data)

    queries = [
        base_query,
        f"{company_hint} руководство контакты email {region}",
    ]

    all_contacts: List[Dict[str, Any]] = []

    for q in queries:
        print(f"[QUERY] {q}")

        res = run_pipeline(
            query=q,
            company_hint=company_hint,
            domain=industry,
            region=region,
            max_urls=15,
            max_results_search=25,
            llm_fallback=True,
        )

        print(f"[PART] {len(res)} contacts")
        all_contacts.extend(res)

    raw_contacts = _dedup_contacts(all_contacts)

    found_ref = order_ref.collection("foundContacts")

    saved = 0

    for c in raw_contacts:
        source = (c.get("source_url") or "").strip()
        email = (c.get("email") or "").strip()
        phone = (c.get("phone") or "").strip()
        full_name = (c.get("full_name") or "").strip()
        position = (c.get("position") or "").strip()

        if not source:
            continue

        if not email and not phone:
            continue

        if position and PHONE_RE.search(position) and not phone:
            phone = position
            position = ""

        doc_data = {
            "fullName": full_name,
            "position": position,
            "email": email,
            "phone": phone,
            "sourceUrl": source,
            "status": "Не проверен",
            "createdAt": firestore.SERVER_TIMESTAMP,
        }

        found_ref.add(doc_data)
        saved += 1

    order_ref.update(
        {
            "status": "Проверка",
            "foundContactsCount": saved,
        }
    )

    print(f"[DONE] Saved {saved} contacts\n")