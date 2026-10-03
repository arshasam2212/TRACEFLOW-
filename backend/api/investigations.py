from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from services import investigation_service as svc
from services.explanation_service import explain
from services.dossier_service import build_pdf
router = APIRouter(prefix="/api/investigations", tags=["investigations"])


class WhatIf(BaseModel):
    account: str


@router.get("/{network_id}")
def investigation(network_id: str):
    return svc.investigation(network_id)


@router.post("/{network_id}/what-if")
def what_if(network_id: str, body: WhatIf):
    return svc.what_if(network_id, body.account)


@router.get("/{network_id}/explanation")
def explanation(network_id: str):
    return explain(svc.net_of(network_id)[1])


@router.get("/{network_id}/dossier")
def dossier(network_id: str, account: str = None, remove: str = None):
    A, net = svc.net_of(network_id)
    inv = svc.investigation(network_id)
    acc = account or net["key_intermediary"]
    pdf = build_pdf(inv, explain(net), svc.what_if(network_id, remove or net["key_intermediary"]), acc)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="TRACEFLOW_{net["case_id"]}.pdf"'})
