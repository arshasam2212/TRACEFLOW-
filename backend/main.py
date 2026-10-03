"""TRACEFLOW API. Run: uvicorn main:app --reload"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from engine.graph_builder import DataError
from services import investigation_service as svc
from api import transactions, networks, accounts, investigations


@asynccontextmanager
async def lifespan(app):
    svc.get()  # demo dataset loads + is analysed once at startup (cached)
    yield

app = FastAPI(title="TRACEFLOW", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for m in (transactions, networks, accounts, investigations):
    app.include_router(m.router)


@app.exception_handler(DataError)
async def data_error(_, e):
    return JSONResponse({"detail": str(e)}, status_code=400)


@app.exception_handler(LookupError)
async def not_found(_, e):
    return JSONResponse({"detail": str(e.args[0]) if e.args else "Not found"}, status_code=404)
