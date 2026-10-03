from fastapi import APIRouter
from services import investigation_service as svc
router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("/{account_id}")
def account(account_id: str):
    return svc.account(account_id)


@router.get("/{account_id}/flow")
def flow(account_id: str):
    return svc.flow(account_id)


@router.get("/{account_id}/replay")
def replay(account_id: str):
    f = svc.flow(account_id)
    if not f["found"]:
        return f
    return dict(found=True, account=account_id, network_id=f["network_id"], final_label=f["label"], frames=f["steps"],
                summary=f["summary"])
