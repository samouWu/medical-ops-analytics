from contextvars import ContextVar
from uuid import uuid4

trace_context: ContextVar[str] = ContextVar("trace_id", default="")


def ok(data=None, message="success"):
    return {"code": 0, "message": message, "data": data, "trace_id": trace_context.get() or uuid4().hex}
