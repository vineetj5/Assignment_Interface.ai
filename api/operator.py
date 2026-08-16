"""Operator API for Phase 7 human handoff."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from handoff.exceptions import HandoffError
from handoff.manager import manager


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
router = APIRouter(tags=["operator"])


class OperatorActionRequest(BaseModel):
    operator_id: str = "operator_demo"


class StartHandoffRunRequest(BaseModel):
    capability: str = "lookup_balance"
    inputs: Dict[str, Any]
    target_url: str | None = None
    headful: bool = False


@router.get("/operator", response_class=HTMLResponse)
async def operator_console(request: Request):
    return templates.TemplateResponse(request=request, name="operator.html", context={})


@router.get("/api/operator/interventions")
@router.get("/operator/api/interventions", include_in_schema=False)
async def list_interventions():
    return {"interventions": [item.model_dump(mode="json") for item in manager.list_open_interventions()]}


@router.get("/api/operator/interventions/{intervention_id}")
@router.get("/operator/api/interventions/{intervention_id}", include_in_schema=False)
async def get_intervention(intervention_id: str):
    intervention = manager.store.get_intervention(intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found.")
    return intervention.model_dump(mode="json")


@router.post("/api/operator/interventions/{intervention_id}/claim")
@router.post("/operator/api/interventions/{intervention_id}/claim", include_in_schema=False)
async def claim_intervention(intervention_id: str, request: OperatorActionRequest):
    intervention = manager.store.get_intervention(intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found.")
    return await claim_run(intervention.run_id, request)


@router.post("/api/operator/interventions/{intervention_id}/resume")
@router.post("/operator/api/interventions/{intervention_id}/resume", include_in_schema=False)
async def resume_intervention(intervention_id: str, request: OperatorActionRequest):
    intervention = manager.store.get_intervention(intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found.")
    return await resume_run(intervention.run_id, request)


@router.post("/api/operator/interventions/{intervention_id}/cancel")
@router.post("/operator/api/interventions/{intervention_id}/cancel", include_in_schema=False)
async def cancel_intervention(intervention_id: str, request: OperatorActionRequest):
    intervention = manager.store.get_intervention(intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found.")
    return await cancel_run(intervention.run_id, request)


@router.get("/api/runs/{run_id}")
@router.get("/operator/api/runs/{run_id}", include_in_schema=False)
async def get_run(run_id: str):
    try:
        return manager.get(run_id).model_dump(mode="json")
    except HandoffError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/runs")
@router.post("/operator/api/runs", include_in_schema=False)
async def start_run(request: StartHandoffRunRequest):
    try:
        handle = await manager.start(
            capability=request.capability,
            inputs=request.inputs,
            headful=request.headful,
            target_url=request.target_url,
        )
        return handle.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/claim")
@router.post("/operator/api/runs/{run_id}/claim", include_in_schema=False)
async def claim_run(run_id: str, request: OperatorActionRequest):
    try:
        intervention = await manager.claim(run_id, request.operator_id)
        return intervention.model_dump(mode="json")
    except HandoffError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/resume")
@router.post("/operator/api/runs/{run_id}/resume", include_in_schema=False)
async def resume_run(run_id: str, request: OperatorActionRequest):
    try:
        result = await manager.resume(run_id, request.operator_id)
        return result.model_dump(mode="json")
    except HandoffError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/cancel")
@router.post("/operator/api/runs/{run_id}/cancel", include_in_schema=False)
async def cancel_run(run_id: str, request: OperatorActionRequest):
    try:
        result = await manager.cancel(run_id, request.operator_id)
        return result.model_dump(mode="json")
    except HandoffError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
