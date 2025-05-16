import os
import streamlit as st
import uuid
from llama_index.core import SimpleDirectoryReader
from llama_index.llms.groq import Groq
from llama_index.embeddings.mistralai import MistralAIEmbedding
from llama_index.core import Settings
from tavily import TavilyClient
from llama_index.core.llms import ChatMessage
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Filter, FieldCondition, MatchValue
from supabase import create_client
import re
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Initialize Supabase client

# API Keys and Configuration
EMBED_API_KEY = "HjheJudiISavtMpy65Yh6m0WTA7bjmVs"
GROQ_API_KEY = "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"
TAVILY_API_KEY = "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"
QDRANT_URL = "https://3d787692-d7d2-4d89-b288-7a309625774e.eu-central-1-0.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.Kzd4YUG6pyLEvDPpL0qX-7rQ8N6C-vbP0HHRfwmRfJM"
SUPABASE_URL = "https://ozajbkuiigfvrhcyekbw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96YWpia3VpaWdmdnJoY3lla2J3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzM3NDQ1ODksImV4cCI6MjA0OTMyMDU4OX0.-btwngaqqQO7wPA_8FAIVeDDcK1pplaIR5DBBlTG1oI"

# Initialize Qdrant client
qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Add Hugging Face configuration
model_id = "intfloat/e5-large-v2"
hf_token = "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"
api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_id}"
headers = {"Authorization": f"Bearer {hf_token}"}

def hide_sidebar():
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"][aria-expanded="true"]{
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

class SupabaseAuthenticator:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    def validate_email(self, email):
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(email_regex, email) is not None

    def validate_password(self, password):
        return (
            len(password) >= 8
            and any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
        )

    def sign_in(self, email, password):
        try:
            if not email or not password:
                st.error("Please fill in all fields")
                return False

            if not self.validate_email(email):
                st.error("Invalid email format")
                return False

            response = self.supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if response.user:
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = email
                st.session_state["user"] = {
                    "id": response.user.id,
                    "email": response.user.email,
                }
                st.success("Login Successful!")
                return True
            else:
                st.error("Login failed. Please check your credentials.")
                return False

        except Exception as e:
            st.error(f"Login error: {str(e)}")
            return False

    def sign_up(self, email, password, name):
        try:
            if not name or not email or not password:
                st.error("Please fill in all fields")
                return False

            if not self.validate_email(email):
                st.error("Invalid email format")
                return False

            if not self.validate_password(password):
                st.error(
                    "Password must be at least 8 characters long and contain uppercase, lowercase, and number"
                )
                return False

            response = self.supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"name": name}},
                }
            )

            if response.user:
                self.supabase.table("profiles").insert(
                    {"id": response.user.id, "name": name, "email": email}
                ).execute()

                st.session_state["signup_success"] = True
                st.success("Account created successfully! Please log in.")
                return True
            else:
                st.error("Signup failed. Please try again.")
                return False

        except Exception as e:
            st.error(f"Signup error: {str(e)}")
            return False

    def sign_out(self):
        try:
            self.supabase.auth.sign_out()
            st.session_state["logged_in"] = False
            st.session_state["user_email"] = None
            if "user" in st.session_state:
                del st.session_state["user"]
            st.success("Logged out successfully")
        except Exception as e:
            st.error(f"Logout error: {str(e)}")

# Keep all existing helper functions
def initialize_llm():
    llm = Groq(model="llama-3.1-8b-instant", api_key=GROQ_API_KEY)
    embed_model = MistralAIEmbedding(model_name="mistral-embed", api_key=EMBED_API_KEY)
    Settings.llm = llm
    Settings.embed_model = embed_model
    return llm

def create_collection_if_not_exists(collection_name, vector_size=1024):
    """Create a Qdrant collection if it does not exist."""
    try:
        collections = qdrant_client.get_collections()
        collection_names = [collection.name for collection in collections.collections]
        
        if collection_name not in collection_names:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance="Cosine")
            )
            print(f"Collection '{collection_name}' created successfully.")
        else:
            print(f"Collection '{collection_name}' already exists.")
    except Exception as e:
        print(f"Error creating/checking collection {collection_name}: {str(e)}")

def initialize_chatbot(uploaded_file, chat_id):
    """Initialize chatbot with uploaded PDF document."""
    # Generate a unique collection name using the chat_id
    collection_name = f"chat_{chat_id}"
    
    # Define the correct embedding dimension based on E5-large-v2 model
    embedding_dimension = 1024  # E5-large-v2 outputs embeddings of size 1024

    # Ensure the collection exists before processing
    create_collection_if_not_exists(collection_name, embedding_dimension)

    with open(f"temp_{chat_id}.pdf", "wb") as f:
        f.write(uploaded_file.getvalue())

    reader = SimpleDirectoryReader(input_files=[f"temp_{chat_id}.pdf"])
    documents = reader.load_data()

    for doc in documents:
        embedding = get_embedding(doc.text)
        point_id = str(uuid.uuid4())
        
        try:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=[PointStruct(
                    id=point_id, 
                    vector=embedding, 
                    payload={
                        "text": doc.text,
                        "type": "document"
                    }
                )]
            )
            print(f"Document inserted with ID: {point_id}")
        except Exception as e:
            print(f"Error inserting document: {str(e)}")

    os.remove(f"temp_{chat_id}.pdf")

def query_chatbot(llm, user_input, tavily_client, chat_id):
    """Query chatbot with user input and store responses."""
    try:
        collection_name = f"chat_{chat_id}"
        
        # Ensure collection exists
        create_collection_if_not_exists(collection_name, 1024)

        # Get query embedding and search Qdrant
        query_embedding = get_embedding(user_input)
        
        # Search for relevant document contexts
        document_search_results = qdrant_client.search(
            collection_name=collection_name, 
            query_vector=query_embedding, 
            limit=3,
            query_filter=Filter(
                must=[FieldCondition(key="type", match=MatchValue(value="document"))]
            )
        )

        # Get contexts and generate response
        retrieved_contexts = [result.payload.get('text', '') for result in document_search_results]
        web_search_response = tavily_client.search(user_input)
        
        # Prepare combined input
        combined_input = user_input
        if retrieved_contexts:
            combined_input += f"\n\nRelevant Document Context: {' '.join(retrieved_contexts)}"
        combined_input += f"\n\nWeb Search Results: {web_search_response}"

        # Generate response
        messages = [
            ChatMessage(
                role="system", 
                content="You are an expert college placement trainer. Use the provided contexts in your response."
            ),
            ChatMessage(role="user", content=combined_input),
        ]

        response = llm.chat(messages).message.content

        # Store conversation in Qdrant for semantic search
        store_rag_data(collection_name, user_input, web_search_response, response)
        
        # Store messages in Supabase for chat history
        store_message(st.session_state['user']['id'], chat_id, "user", user_input)
        store_message(st.session_state['user']['id'], chat_id, "assistant", response)
        
        return response

    except Exception as e:
        print(f"Error in query_chatbot: {e}")
        return fallback_response(llm, user_input)

def retrieve_previous_contexts(collection_name, query_embedding, limit=5):
    """Retrieve previous conversation contexts."""
    try:
        context_filter = Filter(
            must=[
                FieldCondition(
                    key="type",
                    match=MatchValue(value="conversation")
                )
            ]
        )

        search_results = qdrant_client.search(
            collection_name=collection_name, 
            query_vector=query_embedding, 
            limit=limit,
            query_filter=context_filter
        )

        retrieved_contexts = [
            result.payload.get('combined_text', '') 
            for result in search_results
        ]

        return retrieved_contexts
    except Exception as e:
        print(f"Error retrieving previous contexts: {str(e)}")
        return []

def store_rag_data(collection_name, user_input, web_response, llm_response):
    """Store user query, web response, and LLM output in Qdrant."""
    combined_text = f"User Input: {user_input}\nWeb Response: {web_response}\nLLM Response: {llm_response}"
    
    embedding = get_embedding(combined_text)
    point_id = str(uuid.uuid4())
    
    try:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[PointStruct(
                id=point_id, 
                vector=embedding, 
                payload={
                    "combined_text": combined_text,
                    "type": "conversation"
                }
            )]
        )
        print(f"RAG data stored with ID: {point_id}")
    except Exception as e:
        print(f"Error storing RAG data in collection {collection_name}: {str(e)}")

def store_message(user_id, chat_id, role, content):
    """Store a message in Supabase."""
    try:
        data = {
            'user_id': str(user_id),
            'chat_id': int(chat_id),
            'role': str(role),
            'content': str(content)
        }
        
        response = supabase.table('messages').insert(data).execute()
        return True
    except Exception as e:
        print(f"Error storing message: {str(e)}")
        return False

def load_chat_history(user_id, chat_id):
    """Load chat history from Supabase."""
    try:
        # Get all messages for this chat
        response = supabase.table('messages')\
            .select('*')\
            .eq('user_id', str(user_id))\
            .eq('chat_id', int(chat_id))\
            .order('created_at')\
            .execute()

        # Get all chats for this user for sidebar
        chats_response = supabase.table('messages')\
            .select('chat_id')\
            .eq('user_id', str(user_id))\
            .execute()
        
        # Extract unique chat IDs
        chat_ids = list(set(msg['chat_id'] for msg in chats_response.data))
        
        # Update sidebar with chat list
        with st.sidebar:
            st.title("💬 Chat History")
            
            # New Chat button
            if st.button("➕ New Chat"):
                new_chat_id = max(chat_ids, default=0) + 1
                st.session_state.chat_id = new_chat_id
                st.rerun()
            
            # Logout button
            if st.button("🚪 Logout"):
                authenticator = SupabaseAuthenticator()
                authenticator.sign_out()
                st.rerun()
            
            # Display all chats
            st.divider()
            for chat_num in sorted(chat_ids, reverse=True):
                # Get first message from chat for preview
                chat_preview = supabase.table('messages')\
                    .select('content')\
                    .eq('user_id', str(user_id))\
                    .eq('chat_id', chat_num)\
                    .eq('role', 'user')\
                    .order('created_at')\
                    .limit(1)\
                    .execute()
                
                preview_text = chat_preview.data[0]['content'] if chat_preview.data else "Empty chat"
                preview_text = preview_text[:30] + "..." if len(preview_text) > 30 else preview_text
                
                if st.button(
                    f"💭 Chat {chat_num}\n{preview_text}", 
                    key=f"chat_{chat_num}",
                    use_container_width=True
                ):
                    st.session_state.chat_id = chat_num
                    st.rerun()

        return response.data if response.data else []
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []

def chatbot_interface():
    st.set_page_config(page_title="AI Placement Trainer", page_icon="🎓", layout="wide")
    st.title("🎓 AI Placement Trainer")

    # Initialize session state
    if "chat_id" not in st.session_state:
        st.session_state.chat_id = 1
    if "llm" not in st.session_state:
        st.session_state.llm = initialize_llm()
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = str(uuid.uuid4())

    # Load chat history
    messages = load_chat_history(st.session_state['user']['id'], st.session_state.chat_id)

    # Main chat container
    chat_container = st.container()
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload PDF Document (optional)",
        type=["pdf"],
        key=st.session_state.uploader_key,
    )

    if uploaded_file:
        try:
            initialize_chatbot(uploaded_file, st.session_state.chat_id)
            st.success("Document processed successfully!")
        except Exception as e:
            st.error(f"Error processing document: {str(e)}")

    # Display chat history
    for msg in messages:
        with chat_container:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Handle new messages
    user_input = st.chat_input("Ask your placement-related question...")
    if user_input:
        try:
            # Get response (storage is handled inside query_chatbot)
            response = query_chatbot(
                st.session_state.llm,
                user_input,
                TavilyClient(api_key=TAVILY_API_KEY),
                st.session_state.chat_id
            )

            # Display new messages
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(user_input)
                with st.chat_message("assistant"):
                    st.markdown(response)

            st.rerun()  # Refresh to show new messages

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

def login_page(authenticator):
    hide_sidebar()
    st.title("🤖 Groq AI Chatbot - Login")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login", key="login"):
            if authenticator.sign_in(email, password):
                st.rerun()

        st.markdown("---")
        if st.button("Don't have an account? Sign Up"):
            st.session_state["page"] = "signup"
            st.rerun()

def signup_page(authenticator):
    hide_sidebar()
    st.title("🤖 Groq AI Chatbot - Signup")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Sign Up", key="signup"):
            authenticator.sign_up(email, password, name)

        st.markdown("---")
        if st.button("Already have an account? Login"):
            st.session_state["page"] = "login"
            st.rerun()

# Add this after the existing imports
def create_retry_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504],
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

# Update the query function with retry logic
def query(texts):
    """Query the Hugging Face API for embeddings with retry logic."""
    session = create_retry_session()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            prefixed_texts = [f"query: {text}" for text in texts]
            response = session.post(
                api_url,
                headers=headers,
                json={"inputs": prefixed_texts, "options": {"wait_for_model": True}},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ConnectionResetError) as e:
            if attempt == max_retries - 1:
                print(f"Failed to get embedding after {max_retries} attempts: {e}")
                return []
            time.sleep(1 * (attempt + 1))  # Exponential backoff

def get_embedding(text):
    """Get embedding for a single text using Hugging Face API."""
    result = query([text])
    return result[0] if result else []

def fallback_response(llm, user_input):
    """Generate a fallback response when the main query fails."""
    try:
        # Simple system message and user input without additional context
        messages = [
            ChatMessage(
                role="system",
                content="You are an expert college placement trainer. Provide guidance and advice."
            ),
            ChatMessage(role="user", content=user_input),
        ]
        
        final_response = llm.chat(messages)
        return final_response.message.content
    except Exception as e:
        print(f"Error in fallback response: {e}")
        return "I apologize, but I'm having trouble processing your request. Please try again or rephrase your question."

def main():
    authenticator = SupabaseAuthenticator()

    if "user" in st.session_state and st.session_state.get("logged_in"):
        chatbot_interface()
    else:
        if "page" not in st.session_state:
            st.session_state["page"] = "login"

        if st.session_state["page"] == "login":
            login_page(authenticator)
        else:
            signup_page(authenticator)

if __name__ == "__main__":
    main()
