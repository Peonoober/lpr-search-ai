import os
import re
from typing import Any, Dict, List

import firebase_admin
from firebase_admin import credentials, firestore

from src.services.pipeline import run_pipeline

PHONE_RE = re.compile(r"(\+7|8)\s*[\(\-\s]?\d{3}[\)\-\s]?\d{3}[\-\s]?\d{2}[\-\s]?\d{2}")


def _get_project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_db() -> firestore.Client:
    if not firebase_admin._apps:
        json_path = os.path.join(_get_project_root(), "firebase-admin-sdk.json")
        print(f"[DEBUG] Loading Firebase key from: {json_path}")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Service account key not found at {json_path}")
        cred = credentials.Certificate(json_path)
        firebase_admin.initialize_app(cred)
        print("[DEBUG] Firebase Admin initialized")
    return firestore.client()


def _build_search_query(order_data: Dict[str, Any]) -> str:
    criteria = order_data.get("searchCriteria") or {}
    company = (criteria.get("company") or "").strip()
    industry = (criteria.get("industry") or "").strip()
    region = (criteria.get("region") or "").strip()
    details = (criteria.get("details") or "").strip()

    parts: List[str] = []
    if company:
        parts.append(company)
    if industry:
        parts.append(industry)
    if region:
        parts.append(region)
    if details:
        parts.append(details)

    parts.append("(руководство OR ректорат OR директор OR руководитель) (email OR e-mail OR контакты OR phone)")
    return " ".join(parts).strip()


def _dedup_contacts(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    uniq: Dict[str, Dict[str, Any]] = {}
    for c in items:
        email = (c.get("email") or "").lower().strip()
        phone = (c.get("phone") or "").strip()
        source = (c.get("source_url") or c.get("sourceUrl") or "").strip()
        if not source:
            continue
        if not email and not phone:
            continue
        key = email or phone
        if key and key not in uniq:
            uniq[key] = c
    return list(uniq.values())


def start_lpr_search(order_id: str):
    print(f"\n[START] Order {order_id}")
    try:
        db = _get_db()
    except Exception as e:
        print(f"[FATAL] Cannot init Firebase: {e}")
        return

    order_ref = db.collection("orders").document(order_id)

    try:
        snap = order_ref.get()
        if not snap.exists:
            print(f"[ERROR] Order {order_id} not found in Firestore")
            return

        order_data: Dict[str, Any] = snap.to_dict() or {}
        criteria = order_data.get("searchCriteria") or {}

        company_hint = (criteria.get("company") or "").strip()
        industry = (criteria.get("industry") or "").strip()
        region = (criteria.get("region") or "").strip()

        print(f"[DATA] Criteria: company={company_hint} industry={industry} region={region}")

        order_ref.update({"status": "Поиск"})
        print("[STATUS] Set to 'Поиск'")

        base_query = _build_search_query(order_data)
        print(f"[QUERY] {base_query}")

        queries = [
            base_query,
            f'{company_hint} руководство контакты email phone {region}',
            f'{company_hint} ректорат руководство email {region}',
            f'{company_hint} администрация "@" {region}',
        ]

        all_contacts: List[Dict[str, Any]] = []
        for q in queries:
            try:
                print(f"[QUERY2] {q}")
                res = run_pipeline(
                    query=q,
                    company_hint=company_hint,
                    domain=industry,
                    region=region,
                    max_urls=20,
                    max_results_search=35,
                    llm_fallback=True,
                    llm_max_contacts_per_page=25,
                )
                print(f"[PART] {len(res)} contacts")
                all_contacts.extend(res)
            except Exception as e:
                print(f"[WARN] pipeline failed: {e}")
                continue

        raw_contacts = _dedup_contacts(all_contacts)
        print(f"[PIPELINE] Total deduped: {len(raw_contacts)} raw contacts")

        found_ref = order_ref.collection("foundContacts")
        saved = 0

        for c in raw_contacts:
            source = (c.get("source_url") or c.get("sourceUrl") or "").strip()
            email = (c.get("email") or "").strip()
            phone = (c.get("phone") or "").strip()
            full_name = (c.get("full_name") or c.get("fullName") or "").strip()
            position = (c.get("position") or "").strip()
            company = (c.get("company") or company_hint or "").strip()

            if not source:
                continue
            if not email and not phone:
                continue
            if "example.com" in email.lower():
                continue

            if position and PHONE_RE.search(position) and not phone:
                phone = position
                position = ""

            doc_data = {
                "fullName": full_name,
                "position": position,
                "company": company,
                "email": email,
                "phone": phone,
                "sourceUrl": source,
                "status": "Не проверен",
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
            found_ref.add(doc_data)
            saved += 1

        order_ref.update({"status": "Проверка", "foundContactsCount": saved})
        print(f"[DONE] Order {order_id} set to 'Проверка', saved {saved} contacts\n")

    except Exception as e:
        print(f"[EXCEPTION] {type(e).__name__}: {e}")
        try:
            order_ref.update({"status": "Ошибка", "errorMessage": str(e)})
        except Exception:
            pass