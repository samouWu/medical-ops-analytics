from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, analytics, auth, intelligent
from app.api.common import ok, trace_context
from app.core.config import CORS_ORIGINS
from app.core.database import audit, init_db
from app.core.security import token_subject


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="医疗运营数据主题分析平台", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    token = trace_context.set(request.headers.get("X-Trace-ID", uuid4().hex))
    try:
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_context.get()
        path = request.url.path
        if request.method == "GET" and path.startswith("/api/v1") and path not in ("/api/v1/audit/logs", "/api/v1/auth/login"):
            authorization = request.headers.get("Authorization", "")
            username = token_subject(authorization[7:]) if authorization.startswith("Bearer ") else None
            if username:
                try:
                    audit(username, "QUERY_HTTP", path, f"status={response.status_code}", trace_context.get())
                except Exception:
                    pass
        return response
    finally:
        trace_context.reset(token)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code, "message": str(exc.detail), "data": None, "trace_id": trace_context.get()})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": 422, "message": "请求参数校验失败", "data": {"errors": jsonable_encoder(exc.errors())}, "trace_id": trace_context.get()})


@app.exception_handler(PermissionError)
async def permission_error(request: Request, exc: PermissionError):
    return JSONResponse(status_code=403, content={"code": 403, "message": str(exc), "data": None, "trace_id": trace_context.get()})


@app.exception_handler(ValueError)
async def value_error(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"code": 400, "message": str(exc), "data": None, "trace_id": trace_context.get()})


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"code": 500, "message": "服务内部错误，请凭trace_id排查", "data": None, "trace_id": trace_context.get()})


@app.get("/health")
def health():
    return ok({"status": "UP", "service": "medical-ops-analytics"})


@app.get("/")
def root():
    return ok({"name": "医疗运营数据主题分析平台", "docs": "/docs", "health": "/health"})


for router in (auth.router, analytics.router, intelligent.router, admin.router):
    app.include_router(router, prefix="/api/v1")
