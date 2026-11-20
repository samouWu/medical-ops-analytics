from fastapi import APIRouter, HTTPException

from app.api.common import ok, trace_context
from app.core.database import audit, db_session
from app.core.security import create_token, verify_password
from app.schemas import LoginRequest

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
def login(payload: LoginRequest):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM app_user WHERE username=?", (payload.username,)).fetchone()
    if not row or not row["enabled"] or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")
    import json
    user = {"username": row["username"], "display_name": row["display_name"], "role": row["role"], "dept_codes": json.loads(row["dept_codes_json"])}
    audit(row["username"], "LOGIN", "auth", "登录成功", trace_context.get())
    return ok({"token": create_token(row["username"], row["role"]), "user": user})
