from fastapi import APIRouter, UploadFile, File
from services import investigation_service as svc
router = APIRouter(prefix="/api", tags=["transactions"])


@router.get("/dashboard/stats")
def stats():
    return svc.dashboard()


@router.get("/scenarios")
def scenarios():
    return svc.scenarios()


@router.get("/transactions")
def transactions(account: str = None, min_amount: float = 0, limit: int = 100, offset: int = 0):
    A = svc.get(); df = A.df
    if account:
        df = df[(df.sender_account == account) | (df.receiver_account == account)]
    df = df[df.amount >= min_amount]
    ids = df.transaction_id.iloc[offset: offset + min(limit, 500)]
    return dict(total=len(df), items=A.txs(ids))


@router.post("/transactions/upload")
async def upload(file: UploadFile = File(...)):
    A, stages = svc.load_upload(await file.read())
    return dict(ok=True, report=A.report, stats=A.stats, stages=[dict(step=s, seconds=t) for s, t in stages])
