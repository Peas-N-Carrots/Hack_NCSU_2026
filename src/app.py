"""
Phishing Campaign Manager - Admin Interface
A Streamlit app for managing users and campaigns
"""

import streamlit as st

# Page config MUST be first Streamlit command
st.set_page_config(
    page_title="Phishing Campaign Manager",
    layout="wide",
    initial_sidebar_state="expanded"
)

from database import (
    init_database,
    add_user,
    get_all_users,
    get_user_by_email,
    add_sample_email,
    get_sample_emails_for_user,
    create_campaign,
    get_all_campaigns,
    delete_campaign,
    get_campaign_by_id,
    update_campaign,
    get_stats
)
import email
from email import policy
from email.parser import BytesParser

# Initialize database on startup
init_database()

st.title("🎣 Phishing Campaign Manager")
st.markdown("*Educational security awareness training platform*")

# Display overall stats at the top
st.markdown("---")
stats = get_stats()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Users", stats['total_users'])
with col2:
    st.metric("Total Campaigns", stats['total_campaigns'])
with col3:
    st.metric("Emails Sent", stats['total_sent'])
with col4:
    st.metric("Click Rate", f"{stats['click_rate']}%")

st.markdown("---")

# Main layout: Two columns
left_col, right_col = st.columns(2)

# ============================================================================
# LEFT COLUMN - USER MANAGEMENT
# ============================================================================
with left_col:
    st.header("👥 User Management")
    
    # Add new user section
    with st.expander("➕ Add New User", expanded=False):
        new_email = st.text_input("Email Address", key="new_user_email")
        
        # File uploader for sample emails
        st.write("**Upload Sample Emails (Optional)**")
        st.caption("Accepted formats: .eml, .txt, or plain text files")
        uploaded_files = st.file_uploader(
            "Choose email files",
            accept_multiple_files=True,
            type=['eml', 'txt', 'msg'],
            key="sample_emails"
        )
        
        # Manual text input for sample emails
        manual_sample = st.checkbox("Or enter sample email manually", key="manual_sample")
        if manual_sample:
            sample_subject = st.text_input("Sample Email Subject", key="sample_subject")
            sample_body = st.text_area("Sample Email Body", key="sample_body", height=100)
        
        if st.button("Add User", type="primary"):
            if new_email:
                try:
                    # Add the user
                    user_id = add_user(new_email)
                    st.success(f"✅ Added user: {new_email}")
                    
                    # Process uploaded email files
                    if uploaded_files:
                        for uploaded_file in uploaded_files:
                            try:
                                # Read file content
                                file_content = uploaded_file.read()
                                
                                # Try to parse as .eml file
                                if uploaded_file.name.endswith('.eml'):
                                    try:
                                        msg = BytesParser(policy=policy.default).parsebytes(file_content)
                                        subject = msg['subject'] or "No Subject"
                                        body = msg.get_body(preferencelist=('plain')).get_content()
                                    except:
                                        # Fallback: treat as plain text
                                        subject = uploaded_file.name
                                        body = file_content.decode('utf-8', errors='ignore')
                                else:
                                    # Plain text file
                                    subject = uploaded_file.name
                                    body = file_content.decode('utf-8', errors='ignore')
                                
                                # Add to database
                                add_sample_email(user_id, subject, body)
                                st.success(f"  📧 Added sample: {subject}")
                            except Exception as e:
                                st.warning(f"  ⚠️ Could not process {uploaded_file.name}: {str(e)}")
                    
                    # Process manual sample email
                    if manual_sample and sample_subject and sample_body:
                        add_sample_email(user_id, sample_subject, sample_body)
                        st.success(f"  📧 Added manual sample: {sample_subject}")
                    
                    # Wait a moment for user to see success messages, then rerun to clear form
                    import time
                    time.sleep(1)
                    st.rerun()
                    
                except ValueError as e:
                    st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter an email address")
    
    st.markdown("---")
    
    # List existing users
    st.subheader("📋 Existing Users")
    users = get_all_users()
    
    if not users:
        st.info("No users yet. Add one above!")
    else:
        for user in users:
            with st.container():
                # User row with email and delete button
                user_col, delete_col = st.columns([4, 1])
                
                with user_col:
                    st.write(f"**{user['email']}**")
                    
                    # Show sample emails count
                    samples = get_sample_emails_for_user(user['id'])
                    if samples:
                        with st.expander(f"📧 {len(samples)} sample email(s)"):
                            for i, sample in enumerate(samples, 1):
                                st.write(f"**{i}. {sample['subject']}**")
                                st.text(sample['body'][:200] + "..." if len(sample['body']) > 200 else sample['body'])
                                st.caption(f"Uploaded: {sample['uploaded_at']}")
                                st.markdown("---")
                    else:
                        st.caption("No sample emails")
                
                with delete_col:
                    if st.button("🗑️", key=f"delete_user_{user['id']}", 
                               help="Delete this user"):
                        # Note: This will also delete their sample emails due to foreign key
                        # You might want to add a proper delete_user function in database.py
                        # For now, we'll do it directly
                        from database import get_connection
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM sample_emails WHERE user_id = ?", (user['id'],))
                        cursor.execute("DELETE FROM users WHERE id = ?", (user['id'],))
                        conn.commit()
                        conn.close()
                        st.success(f"Deleted user: {user['email']}")
                        st.rerun()
                
                st.markdown("---")

# ============================================================================
# RIGHT COLUMN - CAMPAIGN MANAGEMENT
# ============================================================================
with right_col:
    st.header("📨 Campaign Management")
    
    # Add new campaign section
    with st.expander("➕ Create New Campaign", expanded=False):
        campaign_name = st.text_input("Campaign Name", key="campaign_name", 
                                      placeholder="e.g., Fake Bank Alert")
        
        campaign_template = st.text_area(
            "Email Template", 
            key="campaign_template",
            height=150,
            placeholder="Use {placeholders} for personalization, e.g.:\nDear {name}, your {bank} account needs verification..."
        )
        
        st.write("**Training Links**")
        st.caption("Add links to resources users should review if they click the phishing link")
        
        # Dynamic training links input
        if 'num_links' not in st.session_state:
            st.session_state.num_links = 1
        
        training_links = []
        for i in range(st.session_state.num_links):
            link = st.text_input(f"Link {i+1}", key=f"training_link_{i}", 
                               placeholder="https://training.example.com/phishing-101")
            if link:
                training_links.append(link)
        
        link_col1, link_col2 = st.columns(2)
        with link_col1:
            if st.button("➕ Add Another Link"):
                st.session_state.num_links += 1
                st.rerun()
        with link_col2:
            if st.session_state.num_links > 1:
                if st.button("➖ Remove Last Link"):
                    st.session_state.num_links -= 1
                    st.rerun()
        
        if st.button("Create Campaign", type="primary", key="create_campaign_btn"):
            if campaign_name and campaign_template:
                if not training_links:
                    st.warning("⚠️ Consider adding at least one training link")
                
                campaign_id = create_campaign(
                    name=campaign_name,
                    template_format=campaign_template,
                    training_links=training_links
                )
                st.success(f"✅ Created campaign: {campaign_name} (ID: {campaign_id})")
                
                # Reset form
                st.session_state.num_links = 1
                
                # Wait a moment for user to see success message, then rerun to clear form
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.warning("⚠️ Please fill in campaign name and template")
    
    st.markdown("---")
    
    # List existing campaigns
    st.subheader("📋 Existing Campaigns")
    campaigns = get_all_campaigns()
    
    if not campaigns:
        st.info("No campaigns yet. Create one above!")
    else:
        for campaign in campaigns:
            with st.container():
                # Campaign header with name and delete button
                camp_col, delete_col = st.columns([4, 1])
                
                with camp_col:
                    st.write(f"**{campaign['name']}**")
                
                with delete_col:
                    if st.button("🗑️", key=f"delete_campaign_{campaign['id']}", 
                               help="Delete this campaign"):
                        delete_campaign(campaign['id'])
                        st.success(f"Deleted campaign: {campaign['name']}")
                        st.rerun()
                
                # Campaign details in expander
                with st.expander("View Details", expanded=False):
                    st.write("**Template:**")
                    st.code(campaign['template_format'], language=None)
                    
                    st.write("**Training Links:**")
                    if campaign['training_links']:
                        for i, link in enumerate(campaign['training_links'], 1):
                            st.write(f"{i}. {link}")
                    else:
                        st.caption("No training links")
                    
                    st.caption(f"Created: {campaign['created_at']}")
                    st.caption(f"Campaign ID: {campaign['id']}")
                
                # Send Emails section
                st.write("**📤 Send Campaign**")
                
                # Get all users for selection
                all_users = get_all_users()
                if all_users:
                    # User selection
                    user_options = {f"{user['email']}": user['id'] for user in all_users}
                    selected_users = st.multiselect(
                        "Select recipients",
                        options=list(user_options.keys()),
                        key=f"users_select_{campaign['id']}",
                        placeholder="Choose users to send this campaign to"
                    )
                    
                    send_col1, send_col2 = st.columns([1, 1])
                    with send_col1:
                        if st.button("📧 Send Emails", key=f"send_{campaign['id']}", type="primary"):
                            if selected_users:
                                st.info(f"🚀 Sending campaign to {len(selected_users)} user(s)...")
                                st.write("**Selected recipients:**")
                                for user_email in selected_users:
                                    st.write(f"  - {user_email}")
                                st.success("✅ Campaign queued! Your email sending module will handle delivery.")
                                st.caption("(Connect your Gmail API / email sender here)")
                            else:
                                st.warning("⚠️ Please select at least one user")
                    
                    with send_col2:
                        # Quick "Send to All" option
                        if st.button("📧 Send to All Users", key=f"send_all_{campaign['id']}"):
                            st.info(f"🚀 Sending campaign to all {len(all_users)} users...")
                            st.success("✅ Campaign queued for all users!")
                            st.caption("(Connect your Gmail API / email sender here)")
                else:
                    st.warning("⚠️ No users available. Add users first!")
                
                st.markdown("---")

# Footer
st.markdown("---")
st.caption("🎓 Educational Security Awareness Training Platform | Built for Hackathon 2024")
