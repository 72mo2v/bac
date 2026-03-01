from typing import Optional
from app.core.config import settings

class EmailService:
    def __init__(self):
        # In a real app, setup SMTP or external service (SendGrid/AWS SES)
        self.sender = "no-reply@shop.com"

    async def send_verification_email(self, email: str, token: str):
        link = f"https://shop.com/verify?token={token}"
        print(f"DEBUG: Sending verification email to {email}")
        print(f"DEBUG: Verification link: {link}")
        # Logic to send email goes here

    async def send_welcome_email(self, email: str, name: str):
        print(f"DEBUG: Sending welcome email to {name} ({email})")

    async def send_password_reset_email(self, email: str, token: str):
        link = f"https://shop.com/reset-password?token={token}"
        print(f"DEBUG: Sending password reset email to {email}")
        print(f"DEBUG: Reset link: {link}")

email_service = EmailService()
