from fastapi import APIRouter, HTTPException, BackgroundTasks
from src.services import search_service

router = APIRouter()

@router.post("/orders/{order_id}/search", status_code=202, tags=["Orders"])
def start_search_for_order(order_id: str, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(search_service.start_lpr_search, order_id)
        return {"message": "Процесс поиска успешно запущен в фоновом режиме", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))