from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List

from .config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    SUPPRESS_SEND=settings.SUPPRESS_SEND
)

async def send_verification_email(email_to: EmailStr, code: str):
    """
    Sends a verification code to the specified email address.
    """
    template = f"""
        <html>
            <body>
                <p>Hi there 👋,</p>
                <p>Your 6-digit verification code is: <strong>{code}</strong></p>
                <p>This code will expire in 5 minutes.</p>
                <p>Thanks,<br>Task Planner Team</p>
            </body>
        </html>
    """

    message = MessageSchema(
        subject="Your Task Planner Verification Code",
        recipients=[email_to],
        body=template,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message) 