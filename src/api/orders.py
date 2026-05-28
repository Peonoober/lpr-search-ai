from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from typing import Dict, Any
from src.services import search_service

router = APIRouter()

@router.post("/orders/{order_id}/search", status_code=202, tags=["Orders"])
def start_search_for_order(order_id: str, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(search_service.start_lpr_search, order_id)
        return {
            "message": "Процесс поиска успешно запущен",
            "order_id": order_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/orders/{order_id}/contacts/{contact_id}", tags=["Orders"])
def update_contact(
    order_id: str,
    contact_id: str,
    data: Dict[str, Any] = Body(...)
):
    from src.services.search_service import _get_db

    db = _get_db()

    contact_ref = (
        db.collection("orders")
        .document(order_id)
        .collection("foundContacts")
        .document(contact_id)
    )

    contact_ref.update(data)

    return {"message": "Contact updated successfully"}