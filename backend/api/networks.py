from fastapi import APIRouter
from services import investigation_service as svc
router = APIRouter(prefix="/api/networks", tags=["networks"])


@router.get("")
def networks(pattern: str = None, bank: str = None, risk: str = None, min_amount: float = 0):
    return svc.list_networks(pattern, bank, risk, min_amount)


@router.get("/{network_id}")
def network(network_id: str):
    A, net = svc.net_of(network_id)
    return dict(svc.summary(net), dna=net["dna"], elements=svc.elements(A, net))
