from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List

from .config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
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