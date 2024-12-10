import streamlit as st
from groq import Groq
from datetime import datetime
from supabase import create_client, Client
import uuid
import time

# Hide default page names in sidebar
st.set_page_config(page_title="Groq AI Chatbot")

# Hide streamlit default menu and footer
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="collapsedControl"] {display: none;}
        section[data-testid="stSidebar"] > div:first-child {padding-top: 0rem;}
        .st-emotion-cache-iiif1v {display: none;}
        .st-emotion-cache-1q1z3ya {display: none;}
        div[data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# Supabase Configuration
SUPABASE_URL = "https://ozajbkuiigfvrhcyekbw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96YWpia3VpaWdmdnJoY3lla2J3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzM3NDQ1ODksImV4cCI6MjA0OTMyMDU4OX0.-btwngaqqQO7wPA_8FAIVeDDcK1pplaIR5DBBlTG1oI"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_profile(user_id):
    try:
        response = supabase.table('profiles')\
            .select('*')\
            .eq('id', user_id)\
            .single()\
            .execute()
        return response.data
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None

class RAGSystem:
    def __init__(self):
        self.vector_store = None
    
    def create_vector_store(self):
        """Initialize the vector store"""
        try:
            # For now, return True as if initialization was successful
            return True
        except Exception as e:
            print(f"Error creating vector store: {e}")
            return False
    
    def get_relevant_context(self, query):
        """Get relevant context for a query"""
        # For now, return an empty string
        return ""

# Initialize RAG system
rag_system = RAGSystem()

def initialize_groq_client():
    try:
        client = Groq(api_key="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")
        return client
    except Exception as e:
        st.error(f"Error initializing Groq client: {e}")
        return None


def create_new_chat():
    """Create a new chat and store initial message"""
    try:
        # Get the highest chat_id
        response = supabase.table('messages')\
            .select('chat_id')\
            .eq('user_id', str(st.session_state['user']['id']))\
            .order('chat_id', desc=True)\
            .limit(1)\
            .execute()
        
        new_chat_id = 1
        if response.data:
            new_chat_id = response.data[0]['chat_id'] + 1
        
        print(f"Creating new chat with ID: {new_chat_id}")
        
        # Clear current messages and set new chat_id
        st.session_state.messages = []
        st.session_state.current_chat_id = new_chat_id
        
        return True
    except Exception as e:
        print(f"Error creating new chat: {e}")
        st.error(f"Error creating new chat: {e}")
        return False


def get_groq_response(client, messages, model="llama3-8b-8192"):
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=model
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"Error getting response from Groq: {e}")
        return "I'm sorry, but I encountered an error processing your request."


def load_chat_history(user_id):
    """Load all unique chats for the current user"""
    try:
        # Get all messages for the user
        response = supabase.table('messages')\
            .select('chat_id, content, role')\
            .eq('user_id', str(user_id))\
            .order('created_at')\
            .execute()
        
        if not response.data:
            return []
        
        # Group messages by chat_id
        chat_dict = {}
        for msg in response.data:
            chat_id = msg['chat_id']
            # Only use user messages for preview
            if msg['role'] == 'user' and chat_id not in chat_dict:
                chat_dict[chat_id] = {
                    'id': chat_id,
                    'name': f"Chat {chat_id}",
                    'preview': msg['content'][:30] + "..." if len(msg['content']) > 30 else msg['content']
                }
        
        # Convert to list and sort by chat_id
        chats = list(chat_dict.values())
        chats.sort(key=lambda x: x['id'], reverse=True)  # Sort in descending order
        return chats
    except Exception as e:
        print(f"Error loading chat history: {e}")
        st.error(f"Error loading chat history: {e}")
        return []


def render_chat_history_sidebar():
    with st.sidebar:
        st.header("📜 Chat History")
        
        # New Chat button with unique key
        if st.button("🆕 New Chat", key="new_chat_sidebar"):
            if create_new_chat():
                st.session_state['show_profile'] = False  # Exit profile view
                st.rerun()
        
        # Load chat history from messages table
        if 'user' in st.session_state:
            chats = load_chat_history(st.session_state['user']['id'])
            
            for chat in chats:
                # Show chat name with preview
                button_label = f"💭 {chat['name']}\n{chat['preview']}"
                if st.button(button_label, key=f"chat_history_{chat['id']}"):
                    print(f"Loading messages for chat {chat['id']}")
                    messages = load_chat_messages(st.session_state['user']['id'], chat['id'])
                    if messages:
                        st.session_state.messages = messages
                        st.session_state.current_chat_id = chat['id']
                        st.session_state['show_profile'] = False  # Exit profile view
                        st.rerun()
                    else:
                        print("No messages loaded")
        
        # Profile and Logout Section
        st.markdown("---")
        st.header("👤 User Menu")
        
        if st.button("📋 Profile", key="profile_sidebar"):
            st.session_state['show_profile'] = True
            st.rerun()
            
        if st.button("🚪 Logout", key="logout_sidebar"):
            st.session_state.clear()
            st.session_state["page"] = "login"
            st.switch_page("test.py")


def store_message(user_id, chat_id, role, content):
    """Store a message in the database."""
    try:
        # Print debug information
        print(f"Attempting to store message:")
        print(f"user_id: {user_id}")
        print(f"chat_id: {chat_id}")
        print(f"role: {role}")
        print(f"content: {content}")

        # Ensure user_id is a valid UUID
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        data = {
            'user_id': str(user_id),  # Convert UUID to string
            'chat_id': int(chat_id),  # Ensure chat_id is an integer
            'role': str(role),
            'content': str(content)
        }
        
        print(f"Formatted data: {data}")
        
        response = supabase.table('messages').insert(data).execute()
        print(f"Storage response: {response}")
        return True
    except Exception as e:
        print(f"Detailed error in store_message: {str(e)}")
        st.error(f"Error storing message: {str(e)}")
        return False

def load_chat_messages(user_id, chat_id):
    """Load messages for a specific chat"""
    try:
        print(f"Loading messages for user {user_id} and chat {chat_id}")
        response = supabase.table('messages')\
            .select('*')\
            .eq('user_id', str(user_id))\
            .eq('chat_id', chat_id)\
            .order('created_at')\
            .execute()
        
        # Convert to the format expected by the chat interface
        messages = []
        for msg in response.data:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        print(f"Loaded {len(messages)} messages")
        return messages
    except Exception as e:
        print(f"Error loading messages: {e}")
        st.error(f"Error loading messages: {e}")
        return []

def test_connection():
    try:
        response = supabase.table('messages').select('*').limit(1).execute()
        print(f"Test query successful: {response}")
    except Exception as e:
        print(f"Test query error: {str(e)}")
        st.error(f"Test query error: {str(e)}")

def render_chat_interface():
    """Render the chat interface with messages and input"""
    # Initialize messages in session state if not present
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Initialize current_chat_id if not present
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = 1

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get and display assistant response
        client = initialize_groq_client()
        if client:
            with st.chat_message("assistant"):
                response = get_groq_response(client, st.session_state.messages)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

                # Store messages in database
                if 'user' in st.session_state:
                    store_message(
                        st.session_state['user']['id'],
                        st.session_state.current_chat_id,
                        "user",
                        prompt
                    )
                    store_message(
                        st.session_state['user']['id'],
                        st.session_state.current_chat_id,
                        "assistant",
                        response
                    )

def render_profile():
    """Render the user profile page"""
    st.title("👤 User Profile")
    
    # Initialize session state for update form
    if 'show_update_form' not in st.session_state:
        st.session_state.show_update_form = False
    
    # Get user details from session state
    user = st.session_state['user']
    
    # Fetch profile from database
    profile = get_user_profile(user['id'])
    
    col1, col2, col3 = st.columns([2,1,1])
    
    with col1:
        st.subheader("Profile Information")
        
        # Show current information
        st.text("Current Profile:")
        st.text(f"Name: {profile.get('name', 'Not set') if profile else 'Not set'}")
        st.text(f"Email: {user.get('email', 'Not set')}")
        
        # Button to show update form
        if not st.session_state.show_update_form:
            if st.button("✏️ Update Profile", key="show_update_form_btn"):
                st.session_state.show_update_form = True
                st.rerun()
        
        # Show update form if button clicked
        if st.session_state.show_update_form:
            st.markdown("---")
            st.subheader("Update Profile")
            with st.form("profile_form"):
                # Get current name from profile or user metadata
                current_name = profile.get('name', '') if profile else user.get('user_metadata', {}).get('name', '')
                
                # Name input field with description
                st.text("Enter new name below:")
                new_name = st.text_input("New Name", value=current_name, key="new_name_input")
                
                # Email display (read-only)
                st.text_input("Email (cannot be changed)", value=user.get('email', ''), disabled=True)
                
                col_submit, col_cancel = st.columns([1,1])
                with col_submit:
                    # Form submit button
                    submit = st.form_submit_button("💾 Save Changes")
                with col_cancel:
                    if st.form_submit_button("❌ Cancel"):
                        st.session_state.show_update_form = False
                        st.rerun()
                
                if submit:
                    if new_name.strip() == "":
                        st.error("Name cannot be empty!")
                    else:
                        try:
                            # Update profile in database
                            response = supabase.table('profiles')\
                                .upsert({
                                    'id': user['id'],
                                    'name': new_name,
                                    'email': user.get('email', '')
                                })\
                                .execute()
                                
                            if response:
                                st.success("✅ Profile updated successfully!")
                                # Update session state with new name
                                if 'user_metadata' not in st.session_state['user']:
                                    st.session_state['user']['user_metadata'] = {}
                                st.session_state['user']['user_metadata']['name'] = new_name
                                st.session_state.show_update_form = False  # Hide form after update
                                time.sleep(1)  # Give user time to see success message
                                st.rerun()
                            else:
                                st.error("Failed to update profile")
                        except Exception as e:
                            print(f"Error updating profile: {e}")
                            st.error(f"Error updating profile: {e}")
        
        # Display when the account was created
        created_at = profile.get('created_at', '') if profile else ''
        if created_at:
            st.markdown("---")
            st.text(f"Member since: {created_at[:10]}")
    
    with col2:
        st.subheader("Chat Statistics")
        try:
            # Get message count
            messages = supabase.table('messages')\
                .select('chat_id')\
                .eq('user_id', str(user['id']))\
                .execute()
            
            total_messages = len(messages.data)
            unique_chats = len(set(msg['chat_id'] for msg in messages.data)) if messages.data else 0
            
            st.metric("Total Chats", unique_chats)
            st.metric("Total Messages", total_messages)
        except Exception as e:
            print(f"Error loading chat statistics: {e}")
            st.error("Could not load chat statistics")
    
    with col3:
        st.subheader("Actions")
        # Back to Chat button
        if st.button("← Back to Chat", key="back_to_chat_profile"):
            st.session_state['show_profile'] = False
            st.rerun()
        
        # Logout button
        if st.button("🚪 Logout", key="logout_profile"):
            st.session_state.clear()
            st.session_state["page"] = "login"
            st.switch_page("test.py")

def chatbot_page():
    if 'show_profile' not in st.session_state:
        st.session_state['show_profile'] = False
    
    # Initialize current_chat_id if not present
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = 1
    
    render_chat_history_sidebar()
    
    if st.session_state['show_profile']:
        render_profile()
    else:
        st.title("🤖 Groq AI Chatbot")
        
        # Initialize RAG system if not already done
        if 'rag_initialized' not in st.session_state:
            with st.spinner("Initializing RAG system..."):
                success = rag_system.create_vector_store()
                if success:
                    st.session_state.rag_initialized = True
                    st.success("RAG system initialized successfully!")
                else:
                    st.error("Failed to initialize RAG system")
        
        render_chat_interface()

def main():
    if 'user' not in st.session_state:
        st.error("Please log in to access the chatbot.")
        st.stop()
    
    print(f"User in session: {st.session_state['user']}")
    chatbot_page()

if __name__ == "__main__":
    test_connection()
    main() 
