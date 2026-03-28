import logging
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

logger = logging.getLogger(__name__)

# Build the connection config once from .env settings
mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


class EmailService:
    """
    Centralized email utility following the project's service pattern.
    Any module that needs to send email should import and use this class.
    """

    @staticmethod
    async def send_email(to: list[str], subject: str, body: str) -> None:
        """
        Send a plain-text email to one or more recipients.

        Args:
            to:      List of recipient email addresses.
            subject: Email subject line.
            body:    Plain-text email body.
        """
        if not to:
            return  # Nothing to do

        try:
            message = MessageSchema(
                subject=subject,
                recipients=to,
                body=body,
                subtype=MessageType.plain,
            )
            fm = FastMail(mail_config)
            await fm.send_message(message)
            logger.info(f"Email sent successfully to: {to}")
        except Exception as e:
            # Email failure should NOT crash the API — just log it
            logger.error(f"Failed to send email to {to}: {e}")
