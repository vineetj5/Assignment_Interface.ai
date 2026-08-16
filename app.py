from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from api.chat import router as chat_router
from api.operator import router as operator_router

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "customers.json"

app = FastAPI(title="Northstar Community CU Legacy Demo")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(chat_router)
app.include_router(operator_router)
templates = Jinja2Templates(directory=BASE_DIR / "templates")

with DATA_FILE.open() as f:
    CUSTOMERS = {row["member_id"]: row for row in json.load(f)}

TestCondition = Literal[
    "normal",
    "member_not_found",
    "permission_denied",
    "slow_response",
    "session_expired",
    "unexpected_dialog",
    "app_error",
]


def currency(value: float) -> str:
    return f"${value:,.2f}"


templates.env.filters["currency"] = currency


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"demo_members": ["12345", "76821", "44002"]},
    )


@app.get("/legacy", response_class=HTMLResponse)
def legacy_shell(request: Request):
    return templates.TemplateResponse(request=request, name="legacy_shell.html", context={})


@app.get("/legacy/member-inquiry", response_class=HTMLResponse)
def member_inquiry(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="member_inquiry.html",
        context={
            "member": None,
            "condition": "normal",
            "searched_member_id": "",
            "business_outcome": None,
            "hard_failure": None,
            "show_dialog": False,
        },
    )


@app.post("/legacy/member-search", response_class=HTMLResponse)
def member_search(
    request: Request,
    member_number: str = Form(...),
    test_condition: TestCondition = Form("normal"),
):
    member_number = member_number.strip()

    if test_condition == "slow_response":
        time.sleep(2.2)

    ctx = {
        "member": None,
        "condition": test_condition,
        "searched_member_id": member_number,
        "business_outcome": None,
        "hard_failure": None,
        "show_dialog": False,
    }

    if test_condition == "session_expired":
        ctx["hard_failure"] = {
            "title": "Session Expired",
            "message": "CUCORE session WS-114 expired while processing the request. Sign in again before continuing.",
            "code": "SESSION_EXPIRED",
        }
        return templates.TemplateResponse(request=request, name="member_inquiry.html", context=ctx)

    if test_condition == "permission_denied":
        ctx["hard_failure"] = {
            "title": "Permission Denied",
            "message": "Role MEMBER SERVICE does not have permission to view this member record.",
            "code": "PERMISSION_DENIED",
        }
        return templates.TemplateResponse(request=request, name="member_inquiry.html", context=ctx)

    if test_condition == "app_error":
        ctx["hard_failure"] = {
            "title": "Application Error",
            "message": "CUCORE returned error M1100-E17 while loading the member profile.",
            "code": "APP_ERROR",
        }
        return templates.TemplateResponse(request=request, name="member_inquiry.html", context=ctx)

    if test_condition == "member_not_found" or member_number not in CUSTOMERS:
        ctx["business_outcome"] = {
            "title": "Member Not Found",
            "message": f"No member record was found for member number {member_number}.",
            "code": "MEMBER_NOT_FOUND",
        }
        return templates.TemplateResponse(request=request, name="member_inquiry.html", context=ctx)

    ctx["member"] = CUSTOMERS[member_number]
    ctx["show_dialog"] = test_condition == "unexpected_dialog"
    return templates.TemplateResponse(request=request, name="member_inquiry.html", context=ctx)


@app.get("/legacy/account/{member_id}/{account_type}", response_class=HTMLResponse)
def account_detail(request: Request, member_id: str, account_type: str, cond: str = "normal"):
    member = CUSTOMERS.get(member_id)
    if not member or account_type not in {"savings", "checking"}:
        return RedirectResponse(url="/legacy/member-inquiry", status_code=302)

    account = member["accounts"][account_type]
    return templates.TemplateResponse(
        request=request,
        name="account_detail.html",
        context={
            "member": member,
            "account": account,
            "account_type": account_type,
            "condition": cond,
            "back_url": f"/legacy/member-inquiry?member={quote(member_id)}",
        },
    )


@app.get("/api/mock/customers")
def list_mock_customers():
    """Phase-1 convenience endpoint for developers only; automation should use the UI surface."""
    return {
        "count": len(CUSTOMERS),
        "members": [
            {
                "member_id": m["member_id"],
                "name": m["name"],
                "status": m["status"],
            }
            for m in CUSTOMERS.values()
        ],
    }
