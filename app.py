"""
BTX Welcome Packet Generator - Streamlit Web App with Authentication
Password-protected web interface for generating customer welcome packets from HubSpot data
"""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import requests
from pypdf import PdfReader, PdfWriter
from datetime import datetime
from io import BytesIO
import os

# Page configuration
st.set_page_config(
    page_title="BTX Welcome Packet Generator",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for BTX branding
st.markdown("""
<style>
    .main-header {
        color: #1f4788;
        text-align: center;
        padding: 1rem 0;
    }
    .success-message {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border-color: #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# Load authentication configuration
@st.cache_resource
def load_auth_config():
    """Load authentication configuration from file or secrets"""
    try:
        # Try loading from file first (for local development)
        if os.path.exists('config.yaml'):
            with open('config.yaml') as file:
                return yaml.load(file, Loader=SafeLoader)
        # Fall back to secrets (for deployment)
        elif 'auth' in st.secrets:
            return st.secrets['auth'].to_dict()
        else:
            # Default config if none exists
            return {
                'credentials': {
                    'usernames': {
                        'btx_admin': {
                            'name': 'BTX Admin',
                            'password': '$2b$12$KIXqRlXJUqEqQsaHvlqN1.T7HqJZFjNZ0H3jKqN5qZqN5qZqN5qZ',  # Password: changeme123
                            'email': 'admin@btxglobal.com'
                        }
                    }
                },
                'cookie': {
                    'expiry_days': 30,
                    'key': 'btx_welcome_packet_cookie_key',
                    'name': 'btx_welcome_packet_auth'
                },
                'preauthorized': {
                    'emails': []
                }
            }
    except Exception as e:
        st.error(f"Error loading authentication config: {e}")
        return None


class HubSpotClient:
    """Client for interacting with HubSpot API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_company_by_id(self, company_id):
        """Fetch company details by ID"""
        url = f"{self.base_url}/crm/v3/objects/companies/{company_id}"
        params = {"properties": "name,btx_customer__"}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_company_contacts(self, company_id):
        """Get primary contact for a company"""
        url = f"{self.base_url}/crm/v4/objects/companies/{company_id}/associations/contacts"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        associations = response.json()
        
        if associations.get('results'):
            contact_id = associations['results'][0]['toObjectId']
            return self.get_contact_by_id(contact_id)
        return None
    
    def get_contact_by_id(self, contact_id):
        """Fetch contact details by ID"""
        url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
        params = {"properties": "firstname,lastname,email"}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def search_company_by_name(self, company_name):
        """Search for a company by name"""
        url = f"{self.base_url}/crm/v3/objects/companies/search"
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "name",
                    "operator": "CONTAINS_TOKEN",
                    "value": company_name
                }]
            }],
            "properties": ["name", "btx_customer__"]
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        results = response.json()
        
        if results.get('results'):
            return results['results'][0]
        return None


def fill_btx_welcome_packet(template_file, company_data, contact_data):
    """
    Fill the BTX Welcome Packet PDF template with HubSpot data
    
    Returns: BytesIO object containing the filled PDF
    """
    props = company_data.get('properties', {})
    company_name = props.get('name', 'N/A')
    customer_number = props.get('btx_customer__', 'N/A')
    
    # Get account team (contact name)
    account_team = 'N/A'
    if contact_data:
        contact_props = contact_data.get('properties', {})
        firstname = contact_props.get('firstname', '')
        lastname = contact_props.get('lastname', '')
        account_team = f"{firstname} {lastname}".strip()
        if not account_team:
            account_team = 'N/A'
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    field_values = {
        'Text1': company_name,
        'Text2': customer_number,
        'Text3': account_team,
        'Text4': current_date
    }
    
    # Read and fill the PDF
    reader = PdfReader(template_file)
    writer = PdfWriter()
    
    writer.clone_document_from_reader(reader)
    writer.update_page_form_field_values(writer.pages[0], field_values)
    
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    
    return output, field_values


def main_app():
    """Main application after authentication"""
    
    # Header
    st.markdown('<h1 class="main-header">📄 BTX Global Logistics</h1>', unsafe_allow_html=True)
    st.markdown('<h2 class="main-header">Welcome Packet Generator</h2>', unsafe_allow_html=True)
    
    # User info and logout in sidebar
    with st.sidebar:
        st.write(f"👤 Logged in as: **{st.session_state['name']}**")
        authenticator.logout('Logout', 'main')
        st.markdown("---")
        st.markdown("### ⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "HubSpot API Key",
            type="password",
            help="Enter your HubSpot private app access token",
            value=st.secrets.get("HUBSPOT_API_KEY", "") if "HUBSPOT_API_KEY" in st.secrets else ""
        )
        
        # Template upload
        st.markdown("### 📄 PDF Template")
        uploaded_template = st.file_uploader(
            "Upload BTX Template (Optional)",
            type=['pdf'],
            help="Upload a new template PDF or use the default"
        )
        
        if uploaded_template:
            st.success("✅ Custom template uploaded")
        elif os.path.exists("BTX_Customer_Welcome_PacketCover.pdf"):
            st.info("📄 Using default template")
        else:
            st.warning("⚠️ No template available")
    
    st.markdown("---")
    
    # Main content
    if not api_key:
        st.markdown("""
        <div class="info-box">
        <strong>🔑 Getting Started</strong><br>
        Please enter your HubSpot API key in the sidebar to begin.
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📖 How to get your HubSpot API Key"):
            st.markdown("""
            1. Log into your HubSpot account
            2. Go to **Settings** (gear icon) → **Integrations** → **Private Apps**
            3. Click **Create a private app**
            4. Give it a name (e.g., "Welcome Packet Generator")
            5. Under **Scopes**, select:
               - `crm.objects.companies.read`
               - `crm.objects.contacts.read`
            6. Click **Create app** and copy your Access Token
            7. Paste the token in the sidebar
            """)
        return
    
    # Check for template
    template_file = uploaded_template if uploaded_template else "BTX_Customer_Welcome_PacketCover.pdf"
    
    if not uploaded_template and not os.path.exists(template_file):
        st.error("❌ No PDF template found. Please upload a template in the sidebar.")
        return
    
    # Company search section
    st.subheader("🔍 Find Company")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_method = st.radio(
            "Search Method:",
            ["Search by Name", "Use Company ID"],
            horizontal=True
        )
    
    if search_method == "Search by Name":
        company_input = st.text_input(
            "Company Name",
            placeholder="Enter company name...",
            help="Enter the company name as it appears in HubSpot"
        )
    else:
        company_input = st.text_input(
            "HubSpot Company ID",
            placeholder="Enter company ID...",
            help="Enter the numeric company ID from HubSpot"
        )
    
    # Generate button
    generate_button = st.button("🚀 Generate PDF", type="primary", use_container_width=True)
    
    if generate_button:
        if not company_input:
            st.error("❌ Please enter a company name or ID")
            return
        
        with st.spinner("🔄 Fetching data from HubSpot..."):
            try:
                client = HubSpotClient(api_key)
                
                # Fetch company data
                if search_method == "Search by Name":
                    st.info(f"🔍 Searching for '{company_input}'...")
                    company_data = client.search_company_by_name(company_input)
                    
                    if not company_data:
                        st.error(f"❌ No company found with name: {company_input}")
                        st.info("💡 Try using the HubSpot Company ID instead")
                        return
                    
                    company_id = company_data['id']
                else:
                    company_id = company_input
                    company_data = client.get_company_by_id(company_id)
                
                company_name = company_data['properties']['name']
                st.success(f"✅ Found company: {company_name}")
                
                # Fetch contact data
                st.info("🔍 Fetching account team information...")
                contact_data = client.get_company_contacts(company_id)
                
                if contact_data:
                    contact_props = contact_data['properties']
                    contact_name = f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip()
                    st.success(f"✅ Found account team: {contact_name}")
                else:
                    st.warning("⚠️ No contact associated with this company")
                
                # Generate PDF
                st.info("📝 Filling PDF form...")
                
                if uploaded_template:
                    template_to_use = uploaded_template
                else:
                    with open(template_file, 'rb') as f:
                        template_to_use = BytesIO(f.read())
                
                pdf_output, field_values = fill_btx_welcome_packet(
                    template_to_use,
                    company_data,
                    contact_data
                )
                
                # Display filled values
                st.markdown("### 📋 Filled Information")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Company", field_values['Text1'])
                    st.metric("Customer #", field_values['Text2'])
                
                with col2:
                    st.metric("Account Team", field_values['Text3'])
                    st.metric("Date", field_values['Text4'])
                
                # Download button
                filename = f"BTX_Welcome_Packet_{company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
                
                st.markdown("---")
                st.download_button(
                    label="⬇️ Download Welcome Packet",
                    data=pdf_output,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
                
                st.markdown("""
                <div class="success-message">
                <strong>✨ Success!</strong><br>
                Your Welcome Packet is ready for download.
                </div>
                """, unsafe_allow_html=True)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    st.error("❌ Authentication Error")
                    st.error("Your HubSpot API key is invalid or has expired.")
                    st.info("Please check your API key in the sidebar.")
                elif e.response.status_code == 404:
                    st.error("❌ Not Found")
                    st.error(f"Company or contact not found for: {company_input}")
                else:
                    st.error(f"❌ HubSpot API Error: {e}")
                    st.error(f"Details: {e.response.text}")
                    
            except Exception as e:
                st.error("❌ Unexpected Error")
                st.error(str(e))
                st.info("Please check your inputs and try again.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9em;">
    BTX Global Logistics • Welcome Packet Generator<br>
    For support, contact your IT department
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main entry point with authentication"""
    
    # Load authentication config
    config = load_auth_config()
    
    if config is None:
        st.error("Failed to load authentication configuration")
        return
    
    # Create authenticator
    global authenticator
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    
    # Login widget
    name, authentication_status, username = authenticator.login('Login', 'main')
    
    if authentication_status:
        # User is authenticated - show main app
        main_app()
        
    elif authentication_status == False:
        st.error('❌ Username/password is incorrect')
        st.info('Please check your credentials and try again.')
        
    elif authentication_status == None:
        # Show welcome message for non-authenticated users
        st.markdown('<h1 class="main-header">📄 BTX Global Logistics</h1>', unsafe_allow_html=True)
        st.markdown('<h2 class="main-header">Welcome Packet Generator</h2>', unsafe_allow_html=True)
        st.markdown("---")
        st.info("👆 Please enter your username and password above to continue")
        
        with st.expander("ℹ️ About this application"):
            st.markdown("""
            This application generates professional BTX Welcome Packets by pulling customer 
            information directly from HubSpot. 
            
            **Features:**
            - 🔐 Secure password protection
            - 🔄 Automatic data synchronization with HubSpot
            - 📄 Professional PDF generation
            - 🎨 Branded BTX templates
            - ⚡ Fast and easy to use
            
            **Need access?** Contact your IT administrator.
            """)


if __name__ == "__main__":
    main()
