import io
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import StringIO
from pathlib import Path
from typing import IO

from loguru import logger


class Mailer:
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(self, sender: str, sender_pass: str):
        self.sender_email = sender
        self.sender_pass = sender_pass
        self.subject = ""
        self.body = ""
        self.attachments: list[tuple[IO, str]] = []

    def attach(self, data: IO, attachment_name: str):
        self.attachments.append((data, attachment_name))

    def send(self, to: str):
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = to
        message["Subject"] = self.subject
        message.attach(MIMEText(self.body, "plain"))

        for data, name in self.attachments:
            message.attach(MIMEApplication(data.read(), Name=name))

        try:
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_pass)
                server.send_message(message)
            logger.info(f"Sent email to {to}, subject: {self.subject}")
        except Exception as e:
            logger.warning(f"Error sending email to {to}: {e}")


def test_sending():
    import argparse
    import base64
    import os

    from dotenv import load_dotenv

    parser = argparse.ArgumentParser()
    parser.add_argument("destination_email")
    args = parser.parse_args()

    test_gif_b64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAA2ElEQVR4nOzRLW4CARRF4f6MrKtva1vVpKJJZX1TMQYkAoXCExSKEOQkaBxrIAQWAMGMmC0QloBgDVcdJjmfvk+cvGK9udwlpmUn2s8X3Wj/+beK9g/R+gYZQDOAZgDNAJoBNANoBtCK3aGODpbNb7Q/fmyj/eh1H+1b/wEDaAbQDKAZQDOAZgDNANr9dz2IDl4m42j/Vs2i/c/jOdq3/gMG0AygGUAzgGYAzQCaAbSiPPWig6fmPdp/Pf9H+2HVj/at/4ABNANoBtAMoBlAM4BmAO0aAAD//2wyF8vRvN4gAAAAAElFTkSuQmCC"
    test_gif_bytes = io.BytesIO(base64.b64decode(test_gif_b64))
    test_text_file = StringIO("This is a test text file.")

    load_dotenv()
    mailer = Mailer("gen-ai-bot@lmc-tv.org", os.environ["GMAIL_USER_APP_PASSWORD"])
    mailer.subject = "This is a test email"
    mailer.body = "This is the test email body."
    mailer.attach(test_gif_bytes, "image.gif")
    mailer.attach(test_text_file, "text.txt")
    mailer.send(args.destination_email)


if __name__ == "__main__":
    test_sending()
