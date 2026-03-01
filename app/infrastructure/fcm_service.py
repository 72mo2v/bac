import json
from functools import lru_cache
from typing import Optional, Dict, Any, List

from app.core.config import settings


class FCMService:
    """Best-effort FCM sender. No-ops if not configured."""

    def __init__(self):
        self._enabled = False
        self._app = None
        self._messaging = None
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        project_id = getattr(settings, "FCM_PROJECT_ID", None)
        sa_json = getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", None)
        sa_path = getattr(settings, "FCM_SERVICE_ACCOUNT_PATH", None)
        if not project_id or (not sa_json and not sa_path):
            self._enabled = False
            return

        try:
            import firebase_admin
            from firebase_admin import credentials, messaging
        except Exception:
            self._enabled = False
            return

        try:
            cred = None
            if sa_json:
                cred = credentials.Certificate(json.loads(sa_json))
            else:
                cred = credentials.Certificate(sa_path)

            # Initialize only once per process.
            try:
                self._app = firebase_admin.get_app()
            except Exception:
                self._app = firebase_admin.initialize_app(cred, {"projectId": project_id})

            self._messaging = messaging
            self._enabled = True
        except Exception:
            self._enabled = False

    def enabled(self) -> bool:
        return bool(self._enabled and self._messaging is not None)

    def send_to_tokens(
        self,
        *,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if not self.enabled():
            return None
        if not tokens:
            return None

        # FCM data must be string->string.
        str_data: Dict[str, str] = {}
        if data:
            for k, v in data.items():
                if v is None:
                    continue
                str_data[str(k)] = str(v)

        msg = self._messaging.MulticastMessage(
            tokens=tokens,
            notification=self._messaging.Notification(title=title, body=body),
            data=str_data or None,
        )
        resp = self._messaging.send_multicast(msg)
        return f"success={resp.success_count} failure={resp.failure_count}"


@lru_cache(maxsize=1)
def get_fcm_service() -> FCMService:
    return FCMService()

