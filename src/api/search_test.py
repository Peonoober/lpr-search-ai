from fastapi import APIRouter, Query
from src.tools.web_search import ddg_search_ranked

router = APIRouter()

@router.get("/search/test", tags=["Search"])
def search_test(
    q: str = Query(..., min_length=3),
    n: int = 10
):
    results = ddg_search_ranked(q, max_results=n)
    return {"query": q, "count": len(results), "results": results}