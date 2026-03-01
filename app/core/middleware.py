import time
import uuid
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

# Context Variables for multi-tenancy and tracking
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")
store_id_ctx_var: ContextVar[Optional[int]] = ContextVar("store_id", default=None)

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request_id_ctx_var.set(request_id)
        
        # Extract store_id from headers if present (for multi-tenancy)
        store_id_str = request.headers.get("X-Store-ID")
        if store_id_str and store_id_str.isdigit():
            store_id_ctx_var.set(int(store_id_str))
        else:
            store_id_ctx_var.set(None)

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

def get_request_id() -> str:
    return request_id_ctx_var.get()

def get_store_id() -> Optional[int]:
    return store_id_ctx_var.get()

def set_store_id(store_id: Optional[int]) -> None:
    store_id_ctx_var.set(store_id)
