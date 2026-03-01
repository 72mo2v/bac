from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BasePaymentProvider(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def create_checkout_session(self, amount: float, currency: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a payment session and return checkout URL and session ID."""
        pass

    @abstractmethod
    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify the authenticity of the webhook call."""
        pass

    @abstractmethod
    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the webhook event and return normalized data (status, transaction_id, etc.)."""
        pass

    @abstractmethod
    async def get_payment_status(self, payment_intent_id: str) -> str:
        """Fetch current payment status from the provider."""
        pass
