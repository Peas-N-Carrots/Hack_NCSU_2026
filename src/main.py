from secrets import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, GEMINI_API_KEY
from email_sender import EmailSender
from email_generator import PhishingEmailGenerator

sender = EmailSender(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)

generator = PhishingEmailGenerator(GEMINI_API_KEY)

message = generator.generate_email(
    topic="IT security password reset",
    role="corporate employee",
    difficulty="medium"
)

sender.send(message)

print("Email sent!")
print(f"Subject: {message.subject}")
print(f"Display Name: {message.display_name}")