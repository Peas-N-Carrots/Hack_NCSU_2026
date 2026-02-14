import os
import smtplib
from email.message import EmailMessage

class EmailSender:
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def send(self, msg_model):
        msg = EmailMessage()
        msg["From"] = f"{msg_model.display_name} <{msg_model.from_addr}>"
        msg["To"] = msg_model.to_addr
        msg["Subject"] = msg_model.subject
        msg.set_content(msg_model.body)

        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)
