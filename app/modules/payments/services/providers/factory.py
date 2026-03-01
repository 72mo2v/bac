from typing import Any, Dict
from .base import BasePaymentProvider
from .stripe_provider import StripeProvider

class ProviderFactory:
    @staticmethod
    def get_provider(provider_name: str, config: Dict[str, Any]) -> BasePaymentProvider:
        if provider_name.lower() == "stripe":
            return StripeProvider(config)
        # elif provider_name.lower() == "paypal":
        #     return PayPalProvider(config)
        else:
            raise ValueError(f"Unsupported payment provider: {provider_name}")
