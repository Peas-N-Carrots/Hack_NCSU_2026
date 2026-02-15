"""
email_bridge.py
Bridge module connecting the Streamlit frontend with email sending backend
"""

import os

# Since email_bridge.py is in src/, we can import directly
from database import (
    get_user_by_id,
    get_campaign_by_id,
    log_campaign_sent,
    get_sample_emails_for_user
)

# Import your email modules
try:
    # Import from config.py instead of secrets.py to avoid conflict with built-in secrets module
    from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, GEMINI_API_KEY
    
    from email_sender import EmailSender
    from email_generator import PhishingEmailGenerator
    
    # Initialize sender and generator
    sender = EmailSender(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
    generator = PhishingEmailGenerator(GEMINI_API_KEY)
    EMAIL_MODULES_AVAILABLE = True
except (ImportError, AttributeError) as e:
    print(f"Email modules not available: {e}")
    print(f"Make sure you have config.py in the src/ directory with your credentials")
    EMAIL_MODULES_AVAILABLE = False
    sender = None
    generator = None


def send_campaign_to_users(campaign_id, user_ids, from_addr="teamjam0214@gmail.com"):
    """
    Send a phishing campaign to multiple users using the email generation and sending logic.
    
    Args:
        campaign_id: Campaign ID from database
        user_ids: List of user IDs to send to
        from_addr: Sender email address
        
    Returns:
        dict with results: {
            'success': int,  # number of successful sends
            'failed': int,   # number of failed sends
            'errors': list   # list of error messages
        }
    """
    if not EMAIL_MODULES_AVAILABLE:
        return {
            'success': 0,
            'failed': len(user_ids),
            'errors': ['Email modules not configured. Please set up config.py with SMTP and Gemini credentials.']
        }
    
    # Get campaign details
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        return {
            'success': 0,
            'failed': len(user_ids),
            'errors': [f'Campaign {campaign_id} not found']
        }
    
    results = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    for user_id in user_ids:
        try:
            # Get user details
            user = get_user_by_id(user_id)
            if not user:
                results['failed'] += 1
                results['errors'].append(f"User {user_id} not found")
                continue
            
            to_addr = user['email']
            
            # Log the campaign send in database FIRST to get the result_id
            result_id = log_campaign_sent(campaign_id, user_id)
            
            # Create tracking link that will mark as clicked when user visits
            # Using a simple localhost link for demo - in production you'd use your actual domain
            tracking_link = f"http://localhost:8502?clicked={result_id}"
            
            # Get user's sample emails for context (optional - can be used for personalization)
            samples = get_sample_emails_for_user(user_id)
            
            # Build a better prompt for Gemini that includes sample context and tracking link
            sample_context = ""
            if samples:
                sample_context = "\n\nSample emails from this user for tone/style reference:\n"
                for sample in samples[:2]:  # Use first 2 samples
                    sample_context += f"Subject: {sample['subject']}\n{sample['body'][:200]}\n\n"
            
            # Enhanced prompt for Gemini
            enhanced_prompt = f"""Generate a realistic phishing email based on this scenario:
{campaign['template_format']}

Target email: {to_addr}
{sample_context}

Requirements:
1. Replace ALL placeholders like {{name}}, {{bank}}, {{company}} with realistic values
2. Extract a name from the email address (e.g., john.smith@example.com -> John Smith)
3. Use realistic company/bank names (e.g., Chase Bank, Wells Fargo, Amazon, Microsoft)
4. Include this exact tracking link in the email body: {tracking_link}
5. Make the link look legitimate (e.g., "Click here to verify your account: {tracking_link}")
6. Keep it 2-3 paragraphs, professional tone
7. Include urgency or authority tactics

Output format:
DISPLAY_NAME: <sender name>
SUBJECT: <subject line>
BODY:
<email body with tracking link included>
"""
            
            # Generate the email using Gemini with enhanced prompt
            message = generator.generate_email(
                topic=enhanced_prompt,
                role="user",
                difficulty="medium",
                from_addr=from_addr,
                to_addr=to_addr
            )
            
            # Make sure the tracking link is in the body
            if tracking_link not in message.body:
                message.body = message.body + f"\n\nClick here to verify: {tracking_link}"
            
            # Send the email
            sender.send(message)
            
            results['success'] += 1
            
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"Failed to send to {user.get('email', user_id)}: {str(e)}")
    
    return results


def test_email_config():
    """
    Test if email configuration is set up correctly.
    
    Returns:
        tuple: (is_configured: bool, message: str)
    """
    if not EMAIL_MODULES_AVAILABLE:
        return False, "Email modules not found. Make sure email_sender.py, email_generator.py, and config.py exist in src/"
    
    try:
        # Check if credentials are set
        from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, GEMINI_API_KEY
        
        if not SMTP_HOST or not SMTP_USER or not SMTP_PASS or not GEMINI_API_KEY:
            return False, "Email credentials not configured in config.py"
        
        return True, "Email configuration looks good!"
        
    except Exception as e:
        return False, f"Configuration error: {str(e)}"


if __name__ == "__main__":
    # Test the configuration
    is_configured, message = test_email_config()
    print(f"Configuration test: {message}")
    
    if is_configured:
        print("\nEmail bridge is ready!")
        print("You can now send campaigns from the Streamlit interface.")