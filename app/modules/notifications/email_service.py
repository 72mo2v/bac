from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS
)

class EmailService:
    @staticmethod
    async def send_email(subject: str, email_to: str, body: str):
        try:
            message = MessageSchema(
                subject=subject,
                recipients=[email_to],
                body=body,
                subtype=MessageType.html
            )
            fm = FastMail(conf)
            await fm.send_message(message)
            logger.info(f"Email sent to {email_to} with subject: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email to {email_to}: {str(e)}")

    @staticmethod
    async def send_subscription_expiry_warning(email: str, days_left: int):
        subject = f"Warning: Your subscription expires in {days_left} days"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #4f46e5;">Subscription Expiry Warning</h2>
                    <p>Hello,</p>
                    <p>This is a reminder that your store's subscription will expire in <strong>{days_left} days</strong>.</p>
                    <p>To avoid service interruption, please renew your subscription from the dashboard.</p>
                    <br>
                    <p>Best regards,<br>Platform Team</p>
                </div>
            </body>
        </html>
        """
        await EmailService.send_email(subject, email, body)

    @staticmethod
    async def send_subscription_suspended(email: str):
        subject = "Action Required: Your subscription has been suspended"
        body = """
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #ef4444;">Subscription Suspended</h2>
                    <p>Hello,</p>
                    <p>Your subscription has expired and your store access has been suspended.</p>
                    <p>Please log in and settle your outstanding invoices to reactivate your store.</p>
                    <br>
                    <p>Best regards,<br>Platform Team</p>
                </div>
            </body>
        </html>
        """
        await EmailService.send_email(subject, email, body)
