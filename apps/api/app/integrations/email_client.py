import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as SMTPMessage


@dataclass(frozen=True)
class EmailMessage:
    to: list[str]
    subject: str
    text: str


class SMTPEmailClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender

    def send(self, message: EmailMessage) -> None:
        payload = SMTPMessage()
        payload["From"] = self.sender
        payload["To"] = ", ".join(message.to)
        payload["Subject"] = message.subject
        payload.set_content(message.text)
        with smtplib.SMTP(self.host, self.port, timeout=20) as client:
            client.starttls()
            client.login(self.username, self.password)
            client.send_message(payload)
