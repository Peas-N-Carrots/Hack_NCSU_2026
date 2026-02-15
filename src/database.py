"""
Database module for Phishing Campaign Manager
Handles all database operations using SQLite
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json
import os


# Database file path - store in res directory (one level up from src/)
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'res')
os.makedirs(DB_DIR, exist_ok=True)  # Create res directory if it doesn't exist
DB_PATH = os.path.join(DB_DIR, "phishing_trainer.db")


def get_connection():
    """
    Creates and returns a connection to the SQLite database.
    This is used internally by other functions.
    """
    conn = sqlite3.connect(DB_PATH)
    # This makes results come back as dictionaries instead of tuples
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    Creates all the tables if they don't exist.
    Run this once when starting your app.
    
    Tables:
    - users: Stores registered email addresses
    - sample_emails: Stores sample emails uploaded by users
    - campaigns: Stores campaign templates
    - campaign_results: Tracks who was sent what and if they clicked
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # Sample emails table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT,
            body TEXT,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Campaigns table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            template_format TEXT NOT NULL,
            training_links TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Campaign results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaign_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            sent_at TEXT NOT NULL,
            clicked INTEGER DEFAULT 0,
            completed_training INTEGER DEFAULT 0,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")


# ============================================================================
# USER FUNCTIONS
# ============================================================================

def add_user(email: str) -> int:
    """
    Add a new user to the database.
    
    Args:
        email: User's email address
        
    Returns:
        The ID of the newly created user
        
    Example:
        user_id = add_user("test@example.com")
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    created_at = datetime.now().isoformat()
    
    try:
        cursor.execute(
            "INSERT INTO users (email, created_at) VALUES (?, ?)",
            (email, created_at)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        # Email already exists
        raise ValueError(f"User with email {email} already exists")
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    """
    Get a user by their email address.
    
    Args:
        email: User's email address
        
    Returns:
        Dictionary with user data or None if not found
        
    Example:
        user = get_user_by_email("test@example.com")
        if user:
            print(user['id'], user['email'])
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_all_users() -> List[Dict]:
    """
    Get all users in the database.
    
    Returns:
        List of dictionaries, each containing user data
        
    Example:
        users = get_all_users()
        for user in users:
            print(user['email'])
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """
    Get a user by their ID.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary with user data or None if not found
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


# ============================================================================
# SAMPLE EMAIL FUNCTIONS
# ============================================================================

def add_sample_email(user_id: int, subject: str, body: str) -> int:
    """
    Add a sample email for a user (for personalization).
    
    Args:
        user_id: The user's ID
        subject: Email subject line
        body: Email body text
        
    Returns:
        The ID of the newly created sample email
        
    Example:
        email_id = add_sample_email(1, "Meeting Tomorrow", "Hi, let's meet...")
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    uploaded_at = datetime.now().isoformat()
    
    cursor.execute(
        "INSERT INTO sample_emails (user_id, subject, body, uploaded_at) VALUES (?, ?, ?, ?)",
        (user_id, subject, body, uploaded_at)
    )
    conn.commit()
    email_id = cursor.lastrowid
    conn.close()
    
    return email_id


def get_sample_emails_for_user(user_id: int) -> List[Dict]:
    """
    Get all sample emails for a specific user.
    
    Args:
        user_id: The user's ID
        
    Returns:
        List of dictionaries, each containing sample email data
        
    Example:
        samples = get_sample_emails_for_user(1)
        for sample in samples:
            print(sample['subject'])
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM sample_emails WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ============================================================================
# CAMPAIGN FUNCTIONS
# ============================================================================

def create_campaign(name: str, template_format: str, training_links: List[str]) -> int:
    """
    Create a new phishing campaign template.
    
    Args:
        name: Campaign name (e.g., "Bank Security Alert")
        template_format: The email template with placeholders
        training_links: List of URLs for training resources
        
    Returns:
        The ID of the newly created campaign
        
    Example:
        campaign_id = create_campaign(
            "Fake Bank Alert",
            "Dear {name}, your {bank} account needs verification...",
            ["https://training.com/banking-scams"]
        )
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    created_at = datetime.now().isoformat()
    # Store training links as JSON string
    training_links_json = json.dumps(training_links)
    
    cursor.execute(
        "INSERT INTO campaigns (name, template_format, training_links, created_at) VALUES (?, ?, ?, ?)",
        (name, template_format, training_links_json, created_at)
    )
    conn.commit()
    campaign_id = cursor.lastrowid
    conn.close()
    
    return campaign_id


def get_all_campaigns() -> List[Dict]:
    """
    Get all campaigns.
    
    Returns:
        List of dictionaries, each containing campaign data
        
    Example:
        campaigns = get_all_campaigns()
        for campaign in campaigns:
            print(campaign['name'])
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    campaigns = []
    for row in rows:
        campaign = dict(row)
        # Convert training_links back from JSON string to list
        campaign['training_links'] = json.loads(campaign['training_links'])
        campaigns.append(campaign)
    
    return campaigns


def get_campaign_by_id(campaign_id: int) -> Optional[Dict]:
    """
    Get a campaign by its ID.
    
    Args:
        campaign_id: The campaign's ID
        
    Returns:
        Dictionary with campaign data or None if not found
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        campaign = dict(row)
        campaign['training_links'] = json.loads(campaign['training_links'])
        return campaign
    return None


def update_campaign(campaign_id: int, name: str = None, 
                   template_format: str = None, training_links: List[str] = None) -> bool:
    """
    Update an existing campaign.
    
    Args:
        campaign_id: The campaign's ID
        name: New campaign name (optional)
        template_format: New template (optional)
        training_links: New training links (optional)
        
    Returns:
        True if updated successfully, False if campaign not found
        
    Example:
        update_campaign(1, name="Updated Bank Alert")
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Build update query dynamically based on what's provided
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if template_format is not None:
        updates.append("template_format = ?")
        params.append(template_format)
    if training_links is not None:
        updates.append("training_links = ?")
        params.append(json.dumps(training_links))
    
    if not updates:
        conn.close()
        return False
    
    params.append(campaign_id)
    query = f"UPDATE campaigns SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, params)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    
    return updated


def delete_campaign(campaign_id: int) -> bool:
    """
    Delete a campaign.
    
    Args:
        campaign_id: The campaign's ID
        
    Returns:
        True if deleted successfully, False if campaign not found
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    
    return deleted


# ============================================================================
# CAMPAIGN RESULTS FUNCTIONS
# ============================================================================

def log_campaign_sent(campaign_id: int, user_id: int) -> int:
    """
    Log that a campaign email was sent to a user.
    
    Args:
        campaign_id: The campaign's ID
        user_id: The user's ID
        
    Returns:
        The ID of the newly created result record
        
    Example:
        result_id = log_campaign_sent(1, 5)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    sent_at = datetime.now().isoformat()
    
    cursor.execute(
        "INSERT INTO campaign_results (campaign_id, user_id, sent_at, clicked, completed_training) VALUES (?, ?, ?, 0, 0)",
        (campaign_id, user_id, sent_at)
    )
    conn.commit()
    result_id = cursor.lastrowid
    conn.close()
    
    return result_id


def mark_clicked(result_id: int) -> bool:
    """
    Mark that a user clicked the phishing link.
    
    Args:
        result_id: The campaign result ID
        
    Returns:
        True if updated successfully
        
    Example:
        mark_clicked(10)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE campaign_results SET clicked = 1 WHERE id = ?", (result_id,))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    
    return updated


def mark_training_completed(result_id: int) -> bool:
    """
    Mark that a user completed the training.
    
    Args:
        result_id: The campaign result ID
        
    Returns:
        True if updated successfully
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE campaign_results SET completed_training = 1 WHERE id = ?", (result_id,))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    
    return updated


def get_campaign_results(campaign_id: int) -> List[Dict]:
    """
    Get all results for a specific campaign.
    
    Args:
        campaign_id: The campaign's ID
        
    Returns:
        List of dictionaries with result data including user emails
        
    Example:
        results = get_campaign_results(1)
        for result in results:
            print(f"{result['email']} clicked: {result['clicked']}")
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cr.*,
            u.email,
            c.name as campaign_name
        FROM campaign_results cr
        JOIN users u ON cr.user_id = u.id
        JOIN campaigns c ON cr.campaign_id = c.id
        WHERE cr.campaign_id = ?
        ORDER BY cr.sent_at DESC
    """, (campaign_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_user_results(user_id: int) -> List[Dict]:
    """
    Get all campaign results for a specific user.
    
    Args:
        user_id: The user's ID
        
    Returns:
        List of dictionaries with result data
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cr.*,
            c.name as campaign_name
        FROM campaign_results cr
        JOIN campaigns c ON cr.campaign_id = c.id
        WHERE cr.user_id = ?
        ORDER BY cr.sent_at DESC
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_stats() -> Dict:
    """
    Get overall statistics for the dashboard.
    
    Returns:
        Dictionary with counts and percentages
        
    Example:
        stats = get_stats()
        print(f"Total users: {stats['total_users']}")
        print(f"Click rate: {stats['click_rate']}%")
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total users
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']
    
    # Total campaigns
    cursor.execute("SELECT COUNT(*) as count FROM campaigns")
    total_campaigns = cursor.fetchone()['count']
    
    # Total emails sent
    cursor.execute("SELECT COUNT(*) as count FROM campaign_results")
    total_sent = cursor.fetchone()['count']
    
    # Total clicks
    cursor.execute("SELECT COUNT(*) as count FROM campaign_results WHERE clicked = 1")
    total_clicks = cursor.fetchone()['count']
    
    # Training completions
    cursor.execute("SELECT COUNT(*) as count FROM campaign_results WHERE completed_training = 1")
    total_completed = cursor.fetchone()['count']
    
    conn.close()
    
    click_rate = (total_clicks / total_sent * 100) if total_sent > 0 else 0
    completion_rate = (total_completed / total_clicks * 100) if total_clicks > 0 else 0
    
    return {
        'total_users': total_users,
        'total_campaigns': total_campaigns,
        'total_sent': total_sent,
        'total_clicks': total_clicks,
        'total_completed': total_completed,
        'click_rate': round(click_rate, 2),
        'completion_rate': round(completion_rate, 2)
    }


# ============================================================================
# MAIN - For testing
# ============================================================================

if __name__ == "__main__":
    # Initialize the database
    init_database()
    
    # Test adding a user
    print("\n=== Testing User Functions ===")
    try:
        user_id = add_user("test@example.com")
        print(f"Created user with ID: {user_id}")
    except ValueError as e:
        print(f"User already exists: {e}")
    
    # Get all users
    users = get_all_users()
    print(f"Total users: {len(users)}")
    for user in users:
        print(f"  - {user['email']} (ID: {user['id']})")
    
    # Test adding a sample email
    print("\n=== Testing Sample Email Functions ===")
    if users:
        sample_id = add_sample_email(
            users[0]['id'],
            "Meeting Tomorrow",
            "Hi, let's discuss the project tomorrow at 2pm."
        )
        print(f"Added sample email with ID: {sample_id}")
        
        samples = get_sample_emails_for_user(users[0]['id'])
        print(f"Sample emails for user: {len(samples)}")
    
    # Test creating a campaign
    print("\n=== Testing Campaign Functions ===")
    campaign_id = create_campaign(
        "Fake Bank Alert",
        "Dear {name}, your {bank} account has suspicious activity. Click here to verify.",
        ["https://training.example.com/banking-scams", "https://training.example.com/phishing-101"]
    )
    print(f"Created campaign with ID: {campaign_id}")
    
    campaigns = get_all_campaigns()
    print(f"Total campaigns: {len(campaigns)}")
    for campaign in campaigns:
        print(f"  - {campaign['name']} (ID: {campaign['id']})")
    
    # Test logging a campaign result
    print("\n=== Testing Campaign Results ===")
    if users and campaigns:
        result_id = log_campaign_sent(campaigns[0]['id'], users[0]['id'])
        print(f"Logged campaign sent with result ID: {result_id}")
        
        # Simulate a click
        mark_clicked(result_id)
        print(f"Marked result {result_id} as clicked")
        
        # Get results
        results = get_campaign_results(campaigns[0]['id'])
        print(f"Results for campaign: {len(results)}")
    
    # Get stats
    print("\n=== Overall Stats ===")
    stats = get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")