"""
user_dashboard.py
User Dashboard for Phishing Campaign Manager
Shows campaigns sent to you, your score, and training resources
"""

import streamlit as st

# Page config MUST be first Streamlit command
st.set_page_config(
    page_title="Phishing Training Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

from database import (
    get_user_by_email,
    get_user_results,
    get_campaign_by_id,
    mark_clicked,
    mark_training_completed,
    add_sample_email,
    get_sample_emails_for_user,
    get_all_users
)
import email
from email import policy
from email.parser import BytesParser

# Check if user clicked a phishing link (from URL parameter)
query_params = st.query_params
clicked_result_id = None
if "clicked" in query_params:
    clicked_result_id = int(query_params["clicked"])
    mark_clicked(clicked_result_id)
    st.balloons()
    st.error("🎣 **You've been phished!** This was a training exercise.")
    
    # Get the campaign details and show training resources immediately
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name, c.training_links, u.email
        FROM campaign_results cr
        JOIN campaigns c ON cr.campaign_id = c.id
        JOIN users u ON cr.user_id = u.id
        WHERE cr.id = ?
    """, (clicked_result_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        import json
        campaign_name = row['name']
        training_links = json.loads(row['training_links'])
        user_email = row['email']
        
        st.info(f"📧 Campaign: **{campaign_name}**")
        
        if training_links:
            st.write("**📚 Required Training Resources:**")
            st.write("Please complete these resources to improve your security awareness:")
            for i, link in enumerate(training_links, 1):
                st.markdown(f"### {i}. [Click here for training resource {i}]({link})")
                st.caption(f"Link: {link}")
            
            st.write("---")
            st.write("After completing the training, scroll down and login with your email to mark it complete.")
        else:
            st.warning("No training resources configured for this campaign.")
    
    # Don't clear query params yet - let user see the message
    # st.query_params.clear()

# Title
st.title("🎓 Phishing Awareness Training Dashboard")
st.markdown("*Track your progress and learn to identify phishing attempts*")

# User login section
st.sidebar.header("👤 User Login")
user_email_input = st.sidebar.text_input("Enter your email", key="user_email_login")

if user_email_input:
    user = get_user_by_email(user_email_input)
    
    if not user:
        st.sidebar.error("❌ Email not found. Contact your administrator to register.")
        st.stop()
    
    user_id = user['id']
    st.sidebar.success(f"✅ Logged in as: {user['email']}")
    
    # Get user's results
    results = get_user_results(user_id)
    
    # Calculate user score
    total_sent = len(results)
    total_clicked = sum(1 for r in results if r['clicked'])
    total_not_clicked = total_sent - total_clicked
    training_completed = sum(1 for r in results if r['completed_training'])
    
    if total_sent > 0:
        pass_rate = (total_not_clicked / total_sent) * 100
    else:
        pass_rate = 100
    
    # Display user score
    st.markdown("---")
    st.header("📊 Your Security Score")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Campaigns", total_sent)
    with col2:
        st.metric("✅ Identified as Phishing", total_not_clicked, delta="Good!")
    with col3:
        st.metric("❌ Clicked Phishing Link", total_clicked, delta="Need Training" if total_clicked > 0 else "Great!")
    with col4:
        st.metric("Pass Rate", f"{pass_rate:.1f}%")
    
    # Progress bar
    if total_sent > 0:
        st.progress(pass_rate / 100, text=f"Security Awareness: {pass_rate:.1f}%")
    
    # Display campaigns
    st.markdown("---")
    st.header("📧 Your Phishing Campaign History")
    
    if not results:
        st.info("No campaigns sent to you yet. Check your email!")
    else:
        for result in results:
            campaign = get_campaign_by_id(result['campaign_id'])
            
            with st.expander(
                f"{'❌ CLICKED' if result['clicked'] else '✅ SAFE'} - {result['campaign_name']} (Sent: {result['sent_at'][:10]})",
                expanded=result['clicked'] and not result['completed_training']
            ):
                st.write(f"**Campaign:** {result['campaign_name']}")
                st.write(f"**Sent:** {result['sent_at']}")
                
                if result['clicked']:
                    st.error("⚠️ You clicked the phishing link in this email")
                    
                    # Show training resources
                    if campaign and campaign['training_links']:
                        st.write("**📚 Training Resources:**")
                        st.write("Complete these resources to improve your security awareness:")
                        for i, link in enumerate(campaign['training_links'], 1):
                            st.markdown(f"{i}. [{link}]({link})")
                        
                        # Training completion button
                        if not result['completed_training']:
                            if st.button(f"✅ Mark Training Complete", key=f"complete_{result['id']}"):
                                mark_training_completed(result['id'])
                                st.success("Training marked as complete!")
                                st.rerun()
                        else:
                            st.success("✅ Training completed!")
                    else:
                        st.caption("No training resources available for this campaign")
                else:
                    st.success("✅ Good job! You did not click the phishing link.")
                    st.write("**Why this was phishing:**")
                    st.write("- Urgency and pressure tactics")
                    st.write("- Suspicious sender address")
                    st.write("- Requests for personal information")
                    st.write("- Generic greetings or odd phrasing")
    
    # Upload sample emails section
    st.markdown("---")
    st.header("📤 Upload Your Email Samples")
    st.write("Upload examples of your real emails to help personalize future training campaigns")
    
    with st.expander("➕ Add Sample Emails"):
        uploaded_files = st.file_uploader(
            "Choose email files",
            accept_multiple_files=True,
            type=['eml', 'txt', 'msg'],
            key="user_sample_emails"
        )
        
        # Manual text input for sample emails
        manual_sample = st.checkbox("Or enter sample email manually", key="user_manual_sample")
        if manual_sample:
            sample_subject = st.text_input("Sample Email Subject", key="user_sample_subject")
            sample_body = st.text_area("Sample Email Body", key="user_sample_body", height=100)
        
        if st.button("Upload Samples", type="primary", key="upload_samples_btn"):
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
                        st.success(f"✅ Added sample: {subject}")
                    except Exception as e:
                        st.warning(f"⚠️ Could not process {uploaded_file.name}: {str(e)}")
            
            # Process manual sample email
            if manual_sample and sample_subject and sample_body:
                add_sample_email(user_id, sample_subject, sample_body)
                st.success(f"✅ Added manual sample: {sample_subject}")
            
            if uploaded_files or (manual_sample and sample_subject and sample_body):
                st.rerun()
    
    # Show current sample emails
    samples = get_sample_emails_for_user(user_id)
    if samples:
        with st.expander(f"📧 Your {len(samples)} Sample Email(s)"):
            for i, sample in enumerate(samples, 1):
                st.write(f"**{i}. {sample['subject']}**")
                st.text(sample['body'][:200] + "..." if len(sample['body']) > 200 else sample['body'])
                st.caption(f"Uploaded: {sample['uploaded_at']}")
                st.markdown("---")

else:
    st.info("👆 Enter your email address in the sidebar to view your dashboard")
    st.write("")
    st.write("**What you'll see:**")
    st.write("- Your security awareness score")
    st.write("- History of phishing campaigns sent to you")
    st.write("- Which campaigns you clicked on (fell for)")
    st.write("- Training resources to improve")
    st.write("- Ability to upload email samples")

# Footer
st.markdown("---")
st.caption("🎓 Educational Security Awareness Training Platform | Stay vigilant against phishing!")