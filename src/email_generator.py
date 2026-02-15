# email_generator.py
import os
from google import genai
from email_message import EmailMessageModel


class PhishingEmailGenerator:
    def __init__(self, api_key):
        """
        Initialize the Gemini-based email generator.

        Args:
            api_key: Google Gemini API key
        """
        self.client = genai.Client(api_key=api_key)

    def generate_email(self, topic, role="user", difficulty="medium",
                       from_addr="teamjam0214@gmail.com",
                       to_addr="archristmas10@gmail.com"):
        """
        Generate a phishing email using Gemini API.

        Args:
            topic: The scenario/theme for the phishing email
            role: Target role (e.g., "college student", "corporate employee")
            difficulty: How sophisticated the phishing attempt is
            from_addr: Sender email address
            to_addr: Recipient email address

        Returns:
            EmailMessageModel with generated content
        """
        prompt = f"""
        Generate a realistic phishing email for security awareness training.

        Topic: {topic}
        Target Role: {role}
        Difficulty Level: {difficulty}

        Output format (be precise):
        DISPLAY_NAME: <sender name that appears in email client>
        SUBJECT: <subject line>
        BODY:
        <email body - keep realistic and concise, 2-3 paragraphs max>

        Make it convincing with urgency or authority tactics.
        """

        response = self.client.models.generate_content(
            model="gemini-flash-latest",  # This is available!
            contents=prompt
        )

        text = response.candidates[0].content.parts[0].text
        parsed = self._parse_response(text)

        return EmailMessageModel(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=parsed['subject'],
            body=parsed['body'],
            display_name=parsed['display_name']
        )

    def _parse_response(self, text):
        """Parse Gemini's response into structured data."""
        lines = text.strip().split('\n')

        display_name = ""
        subject = ""
        body_lines = []
        in_body = False

        for line in lines:
            line = line.strip()
            if line.startswith("DISPLAY_NAME:"):
                display_name = line.replace("DISPLAY_NAME:", "").strip()
            elif line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                in_body = True
            elif in_body:
                body_lines.append(line)

        return {
            'display_name': display_name or "Security Team",
            'subject': subject or "Important Account Notice",
            'body': '\n'.join(body_lines).strip()
        }


if __name__ == "__main__":
    # Test the generator
    from src.secrets import GEMINI_API_KEY

    generator = PhishingEmailGenerator(GEMINI_API_KEY)

    message = generator.generate_email(
        topic="account suspension",
        role="college student",
        difficulty="medium"
    )

    print("=" * 60)
    print("GENERATED EMAIL")
    print("=" * 60)
    print(f"Display Name: {message.display_name}")
    print(f"Subject: {message.subject}")
    print(f"\nBody:")
    print("-" * 60)
    print(message.body)
    print("-" * 60)