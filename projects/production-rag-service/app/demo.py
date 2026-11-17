"""Small, read-only public demo corpus for the AtlasRAG showcase."""
from collections import deque
from threading import Lock
from time import monotonic
from typing import Any
from fastapi import HTTPException, Request
from .answering import build_grounded_answer
from .schemas import Citation, QueryIn, QueryResponse
from .retrieval import BM25Retriever

DEMO_DOCUMENTS: list[dict[str, Any]] = [
 {"chunk_id":"demo-handbook:0","document_id":"demo-handbook","title":"Northstar Employee Handbook","source":"demo://employee-handbook","text":"Northstar employees may work remotely up to three days per week with manager approval. Teams should agree on their shared office days at the start of each quarter. Employees handling confidential customer data must use company-managed devices and the approved VPN."},
 {"chunk_id":"demo-security:0","document_id":"demo-security","title":"Information Security Standard","source":"demo://security-standard","text":"All production access requires multi-factor authentication. API keys must be stored in the approved secret manager, rotated every 90 days, and never committed to source control. Security incidents must be reported to the security team within one hour of discovery."},
 {"chunk_id":"demo-expenses:0","document_id":"demo-expenses","title":"Travel and Expense Policy","source":"demo://travel-expenses","text":"Business travel must be approved by the employee's manager before booking. Expense claims should be submitted within 15 calendar days after the trip. Receipts are required for individual expenses above 25 euros. Economy class is the standard for flights under six hours."},
 {"chunk_id":"demo-onboarding:0","document_id":"demo-onboarding","title":"Engineering Onboarding Guide","source":"demo://engineering-onboarding","text":"New engineers receive access to the development environment after completing security training and signing the equipment policy. The first-week onboarding plan includes architecture review, local setup, a pairing session, and a small documentation contribution. Production deployments require a reviewed pull request and passing CI checks."},
 {"chunk_id":"demo-fa:0","document_id":"demo-fa","title":"راهنمای دورکاری","source":"demo://remote-work-fa","text":"کارکنان شرکت نورث‌استار با تأیید مدیر خود می‌توانند حداکثر سه روز در هفته دورکاری کنند. اطلاعات محرمانه مشتریان باید فقط روی دستگاه مدیریت‌شده شرکت و از طریق شبکه امن پردازش شود. درخواست هزینه سفر باید حداکثر تا پانزده روز پس از پایان سفر ثبت شود."},
]
_DEMO_RANKER = BM25Retriever()
_WINDOW_SECONDS = 60
_MAX_REQUESTS_PER_WINDOW = 20

def check_demo_rate_limit(request: Request) -> None:
    """Apply a conservative per-client, in-memory limit to the read-only demo."""
    now = monotonic()
    client_key = request.client.host if request.client else "unknown"
    lock: Lock = request.app.state.demo_rate_limit_lock
    windows: dict[str, deque[float]] = request.app.state.demo_rate_limit_windows
    with lock:
        window = windows.setdefault(client_key, deque())
        while window and now - window[0] >= _WINDOW_SECONDS:
            window.popleft()
        if len(window) >= _MAX_REQUESTS_PER_WINDOW:
            raise HTTPException(status_code=429, detail="Demo rate limit reached. Please try again in a minute.", headers={"Retry-After":"60"})
        window.append(now)

def list_demo_documents() -> list[dict[str, str]]:
    return [{"document_id":x["document_id"],"title":x["title"],"source":x["source"],"language":"fa" if x["document_id"]=="demo-fa" else "en"} for x in DEMO_DOCUMENTS]

def query_demo(payload: QueryIn) -> QueryResponse:
    results = _DEMO_RANKER.search(payload.question, DEMO_DOCUMENTS, min(payload.top_k or 3, 5))
    citations = [Citation(chunk_id=x["chunk_id"],document_id=x["document_id"],title=x["title"],source=x["source"],text=x["text"],score=round(x["score"],6)) for x in results]
    return QueryResponse(answer=build_grounded_answer(payload.question,results),grounded=bool(results),citations=citations,retrieval_method="demo_bm25")
