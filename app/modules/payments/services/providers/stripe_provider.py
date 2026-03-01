import stripe
from typing import Any, Dict, Optional
from .base import BasePaymentProvider

class StripeProvider(BasePaymentProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.webhook_secret = config.get("webhook_secret")
        stripe.api_key = self.api_key

    async def create_checkout_session(self, amount: float, currency: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Note: Stripe expects amount in cents
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': metadata.get('plan_name', 'Subscription payment'),
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=metadata.get('success_url'),
                cancel_url=metadata.get('cancel_url'),
                metadata=metadata,
                client_reference_id=str(metadata.get('payment_id'))
            )
            return {
                "checkout_url": session.url,
                "provider_session_id": session.id,
                "provider_payment_intent": session.payment_intent
            }
        except Exception as e:
            raise Exception(f"Stripe session creation failed: {str(e)}")

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        try:
            stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return True
        except stripe.error.SignatureVerificationError:
            return False
        except Exception:
            return False

    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        event_type = event_data.get("type")
        data_object = event_data.get("data", {}).get("object", {})
        
        normalized = {
            "event_type": event_type,
            "status": "unknown",
            "transaction_id": data_object.get("id"),
            "payment_intent": data_object.get("payment_intent"),
            "amount": data_object.get("amount_total", 0) / 100 if "amount_total" in data_object else 0,
            "metadata": data_object.get("metadata", {})
        }

        if event_type == "checkout.session.completed":
            normalized["status"] = "success"
        elif event_type == "payment_intent.payment_failed":
            normalized["status"] = "failed"
            normalized["failure_reason"] = data_object.get("last_payment_error", {}).get("message")
        
        return normalized

    async def get_payment_status(self, payment_intent_id: str) -> str:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return intent.status
        except Exception:
            return "unknown"
