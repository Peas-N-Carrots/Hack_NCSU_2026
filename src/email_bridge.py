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
            'errors': ['Email modules not configured. Please set up secrets.py with SMTP and Gemini credentials.']
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
            
            # Get user's sample emails for context (optional - can be used for personalization)
            samples = get_sample_emails_for_user(user_id)
            
            # Generate the email using Gemini
            # Use the campaign name as the "topic" for generation
            # The template could be used for additional context, but since your generator
            # creates the whole email, we'll use the campaign name as the topic
            message = generator.generate_email(
                topic=campaign['template_format'],  # Use the template as the topic/scenario
                role="user",  # Could be customized based on user data
                difficulty="medium",
                from_addr=from_addr,
                to_addr=to_addr
            )
            
            # Send the email
            sender.send(message)
            
            # Log the campaign send in database
            log_campaign_sent(campaign_id, user_id)
            
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