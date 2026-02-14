# This will be for generating email contents with the Gemini API
import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def generate_phishing_email(topic, role="user", difficulty="medium"):
    prompt = f"""
    Generate a realistic phishing email.

    Topic: {topic}
    Target: {role}
    Difficulty: {difficulty}

    Output format:
    Subject: <subject line>
    Body:
    <email body>

    Keep it short and realistic.
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.candidates[0].content.parts[0].text


if __name__ == "__main__":
    email = generate_phishing_email(
        topic="account suspension",
        role="college student",
        difficulty="medium"
    )
    print(email)