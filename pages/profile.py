import streamlit as st
from supabase import create_client

# Supabase Configuration
SUPABASE_URL = "https://ozajbkuiigfvrhcyekbw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96YWpia3VpaWdmdnJoY3lla2J3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzM3NDQ1ODksImV4cCI6MjA0OTMyMDU4OX0.-btwngaqqQO7wPA_8FAIVeDDcK1pplaIR5DBBlTG1oI"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def profile_page():
    if 'user' not in st.session_state:
        st.error("Please log in to view your profile")
        st.stop()
    
    st.title("👤 User Profile")
    
    # Get user details from session state
    user = st.session_state['user']
    
    col1, col2 = st.columns([2,1])
    
    with col1:
        st.subheader("Profile Information")
        st.text(f"Name: {user.get('user_metadata', {}).get('name', 'Not set')}")
        st.text(f"Email: {user.get('email', 'Not set')}")
        st.text(f"User ID: {user.get('id', 'Not set')}")
        
        # Display when the account was created
        created_at = user.get('created_at', '')
        if created_at:
            st.text(f"Member since: {created_at[:10]}")
    
    with col2:
        st.subheader("Chat Statistics")
        try:
            # Get message count
            messages = supabase.table('Messages')\
                .select('chat_id')\
                .eq('user_id', user['id'])\
                .execute()
            
            total_messages = len(messages.data)
            unique_chats = len(set(msg['chat_id'] for msg in messages.data))
            
            st.metric("Total Chats", unique_chats)
            st.metric("Total Messages", total_messages)
        except Exception as e:
            st.error("Could not load chat statistics")
    
    # Back to Chat button
    if st.button("← Back to Chat"):
        st.session_state['current_page'] = 'chat'
        st.rerun()

if __name__ == "__main__":
    profile_page() 
