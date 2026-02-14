from secrets import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
from email_sender import EmailSender
from email_message import EmailMessageModel

sender = EmailSender(
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS
)

message = EmailMessageModel(
    from_addr="teamjam0214@gmail.com",
    to_addr="archristmas10@gmail.com",
    subject="Test Email",
    body="If you see this in Mailtrap, it worked.",
    display_name="Security Training"
)

sender.send(message)

print("Email sent!")
