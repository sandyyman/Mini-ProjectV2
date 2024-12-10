import streamlit as st
from supabase import create_client
import re

# Supabase Configuration
SUPABASE_URL = "https://ozajbkuiigfvrhcyekbw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96YWpia3VpaWdmdnJoY3lla2J3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzM3NDQ1ODksImV4cCI6MjA0OTMyMDU4OX0.-btwngaqqQO7wPA_8FAIVeDDcK1pplaIR5DBBlTG1oI"


def hide_sidebar():
    """Hide the sidebar using custom CSS"""
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
        # Initialize Supabase client
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    def validate_email(self, email):
        """Validate email format"""
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(email_regex, email) is not None

    def validate_password(self, password):
        """Validate password strength"""
        # At least 8 characters, one uppercase, one lowercase, one number
        return (
            len(password) >= 8
            and any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
        )

    def sign_in(self, email, password):
        """Sign in user"""
        try:
            # Validate inputs
            if not email or not password:
                st.error("Please fill in all fields")
                return False

            if not self.validate_email(email):
                st.error("Invalid email format")
                return False

            # Attempt to sign in
            try:
                response = self.supabase.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )

                if response.user:
                    # Store user details in session state
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = email
                    st.session_state["user"] = {
                        "id": response.user.id,
                        "email": response.user.email,
                    }
                    st.success("Login Successful!")
                    # Redirect to chatbot page
                    st.switch_page(
                        "pages/chatbot.py"
                    )  # Make sure chatbot.py is in the 'pages' folder
                    return True
                else:
                    st.error("Login failed. Please check your credentials.")
                    return False

            except Exception as auth_error:
                print(f"Authentication error details: {auth_error}")
                st.error(f"Authentication error: {str(auth_error)}")
                return False

        except Exception     as e:
            print(f"General login error: {e}")
            st.error(f"Login error: {str(e)}")
            return False

    def sign_up(self, email, password, name):
        """Sign up a new user"""
        try:
            # Validate inputs
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

            # Create auth user
            response = self.supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"name": name}},
                }
            )

            if response.user:
                # Insert user data into profiles table
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
        """Log out the current user"""
        try:
            self.supabase.auth.sign_out()
            # Clear all authentication-related session states
            st.session_state["logged_in"] = False
            st.session_state["user_email"] = None
            if "user" in st.session_state:
                del st.session_state["user"]
            st.success("Logged out successfully")
        except Exception as e:
            st.error(f"Logout error: {str(e)}")


def login_page(authenticator):
    """Render the login page."""
    hide_sidebar()  # Hide sidebar on login page

    st.title("🤖 Groq AI Chatbot - Login")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login", key="login"):
            authenticator.sign_in(email, password)

        st.markdown("---")
        if st.button("Don't have an account? Sign Up"):
            st.session_state["page"] = "signup"
            st.rerun()


def signup_page(authenticator):
    """Render the signup page."""
    hide_sidebar()  # Hide sidebar on signup page

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


def main():
    # Initialize Supabase Authenticator
    authenticator = SupabaseAuthenticator()

    # Check if user is logged in
    if "user" in st.session_state and st.session_state.get("logged_in"):
        # Redirect to chatbot page
        st.switch_page("pages/chatbot.py")
    else:
        # Show login or signup page based on session state
        if "page" not in st.session_state:
            st.session_state["page"] = "login"

        if st.session_state["page"] == "login":
            login_page(authenticator)
        else:
            signup_page(authenticator)


if __name__ == "__main__":
    main()
