from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import SECRET_KEY, TOKEN_MINUTES

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_token(username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": username, "role": role, "iat": now, "exp": now + timedelta(minutes=TOKEN_MINUTES)}, SECRET_KEY, algorithm="HS256")


def token_subject(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if not credentials:
        raise HTTPException(401, "请先登录")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "登录状态已失效") from None
    from app.core.database import get_user
    user = get_user(payload["sub"])
    if not user or not user["enabled"]:
        raise HTTPException(401, "用户不可用")
    return user


def require_roles(*roles: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, "当前角色无权执行此操作")
        return user
    return dependency


def check_department_scope(user: dict, dept_code: str | None) -> None:
    allowed = user.get("dept_codes") or []
    if allowed and dept_code and dept_code not in allowed:
        raise HTTPException(403, "无权访问该科室数据")
