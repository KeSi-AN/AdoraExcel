import os
import streamlit as st
import pandas as pd
import time
from pathlib import Path
from datetime import datetime
import json

# Import our modules
from models import ExcelFile, ExcelTable
import database as db
import excel_parser as parser
from serializers import serialize_data, prepare_for_db
from ai_utils import generate_chat_response, analyze_table

# Configuration
UPLOAD_FOLDER = "excel_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database
db.init_db()

# Page configuration
st.set_page_config(
    page_title="Excel ChatBot", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .file-card { border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
    .file-card:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .stButton>button { width: 100%; margin: 5px 0; }
    .chat-message { padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .chat-message.user { background-color: #e3f2fd; }
    .chat-message.assistant { background-color: #f5f5f5; }
    .table-container { margin: 10px; padding: 10px; border: 1px solid #eee; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

def clean_dataframe(df):
    """Clean DataFrame by removing all-null columns and converting to string."""
    # Remove columns where all values are null/empty
    df_cleaned = df.dropna(axis=1, how='all')
    # Convert all data to string for consistent display
    return df_cleaned.astype(str)

def initialize_session_state():
    """Initialize session state variables."""
    if 'page' not in st.session_state:
        st.session_state.page = 'upload'
    if 'selected_file_id' not in st.session_state:
        st.session_state.selected_file_id = None
    if 'selected_sheet' not in st.session_state:
        st.session_state.selected_sheet = None
    if 'tables_data' not in st.session_state:
        st.session_state.tables_data = {}
    if 'processing_file' not in st.session_state:
        st.session_state.processing_file = False
    if 'upload_success' not in st.session_state:
        st.session_state.upload_success = None
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = {}  # Store chat messages by unique key



# Initialize session state
initialize_session_state()

def show_upload_page():
    """Render the file upload page."""
    if st.session_state.page != 'upload':
        return
    
    st.title("📤 Upload New Excel File")
    
    # Display any existing success message
    if st.session_state.upload_success:
        file_id = st.session_state.upload_success.get('file_id')
        tables_data = st.session_state.upload_success.get('tables_data')
        
        st.success("Excel file processed successfully!")
        st.subheader("Tables Found")
        
        # Display table summary
        for sheet_name, tables in tables_data.items():
            with st.expander(f"📑 Sheet: {sheet_name}"):
                st.write(f"Found {len(tables)} tables")
                for table_name, table_data in tables.items():
                    with st.container():
                        st.markdown(f"**Table:** {table_name}")
                        df = pd.DataFrame(table_data)
                        df_cleaned = clean_dataframe(df)
                        # Display the table
                        st.dataframe(df_cleaned)
                        
                        # Download button
                        csv = df_cleaned.to_csv(index=False).encode('utf-8')
                        # Get the original file name from the session state or use a default
                        file_name = "table_data"
                        if 'uploaded_file_name' in st.session_state:
                            file_name = os.path.splitext(st.session_state.uploaded_file_name)[0]
                        elif 'upload_success' in st.session_state and st.session_state.upload_success:
                            file_name = os.path.splitext(st.session_state.upload_success.get('file_name', 'table_data'))[0]
                            
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=f"{file_name}_{sheet_name}_{table_name}.csv",
                            mime='text/csv',
                            key=f"dl_upload_{sheet_name}_{table_name}",
                            use_container_width=True
                        )
                        
                        # Inline chat interface
                        st.markdown("---")
                        st.subheader("💬 Chat with this Table")
                        
                        # Create a unique key for this chat
                        chat_key = f"upload_{sheet_name}_{table_name}"
                        
                        # Initialize chat messages if not exists
                        if chat_key not in st.session_state.chat_messages:
                            st.session_state.chat_messages[chat_key] = [
                                {"role": "assistant", "content": f"Ask me anything about this table: {table_name}"}
                            ]
                        
                        # Display chat messages
                        for msg in st.session_state.chat_messages[chat_key]:
                            with st.chat_message(msg["role"]):
                                st.write(msg["content"])
                        
                        # Chat input with a fixed key
                        if prompt := st.chat_input("Ask about this table...", key=f"chat_input_{chat_key}"):
                            with st.spinner("Analyzing table..."):
                                # Add user message
                                st.session_state.chat_messages[chat_key].append(
                                    {"role": "user", "content": prompt}
                                )
                                
                                # Generate AI response with table context
                                response = analyze_table(
                                    df_cleaned, 
                                    f"{prompt} - Answer based on this table: {table_name} in sheet: {sheet_name}"
                                )
                                
                                # Add assistant response
                                st.session_state.chat_messages[chat_key].append(
                                    {"role": "assistant", "content": response}
                                )
                                st.rerun()
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("📋 View All Files", use_container_width=True):
                st.session_state.page = 'browse'
                st.session_state.upload_success = None
                st.rerun()
        with col2:
            if st.button("💬 Chat with Tables", use_container_width=True):
                st.session_state.selected_file_id = file_id
                st.session_state.tables_data = tables_data
                st.session_state.page = 'chat'
                st.session_state.upload_success = None
                st.rerun()
        
        # Add a separator
        st.markdown("---")
        st.subheader("Upload Another File")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    if uploaded_file and not st.session_state.get('processing_file', False):
        st.session_state.processing_file = True
        # Store the uploaded file name in session state
        st.session_state.uploaded_file_name = uploaded_file.name
        
        try:
            with st.spinner("Processing file..."):
                # Save the uploaded file
                file_path, file_hash = parser.save_uploaded_file(uploaded_file, UPLOAD_FOLDER)
                
                # Check for duplicate
                if db.is_duplicate_file(file_hash):
                    st.warning("This file has already been uploaded.")
                    os.remove(file_path)
                    st.session_state.processing_file = False
                    return
                
                # Extract tables from the Excel file
                tables_data = parser.extract_all_tables(file_path)
                
                if not tables_data:
                    st.error("No tables found in the Excel file.")
                    os.remove(file_path)
                    st.session_state.processing_file = False
                    return
                
                # Save to database
                try:
                    file_id = db.save_excel_file(
                        file_name=os.path.basename(file_path),
                        file_path=file_path,
                        file_hash=file_hash,
                        tables_data=tables_data
                    )
                    
                    # Store success state in session
                    st.session_state.upload_success = {
                        'file_id': file_id,
                        'tables_data': tables_data
                    }
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error saving to database: {str(e)}")
                    if os.path.exists(file_path):
                        os.remove(file_path)
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        finally:
            st.session_state.processing_file = False

def show_browse_page():
    """Render the file browser page."""
    # Check if we're viewing a specific file's tables
    if 'viewing_file_id' in st.session_state and st.session_state.viewing_file_id:
        file_data = db.get_excel_file(st.session_state.viewing_file_id)
        if file_data:
            # Back button
            if st.button("← Back to All Files"):
                st.session_state.viewing_file_id = None
                st.rerun()
            
            st.title(f"📄 {file_data['file_name']}")
            st.caption(f"Uploaded: {file_data['uploaded_at']}")
            
            # Display tables using the same style as upload page
            if file_data['tables']:
                sheet_names = list(file_data['tables'].keys())
                tabs = st.tabs([f"📑 {name}" for name in sheet_names])
                
                for idx, (sheet_name, tables) in enumerate(file_data['tables'].items()):
                    with tabs[idx]:
                        st.subheader(f"{sheet_name}")
                        
                        # Create tabs for tables within each sheet
                        if tables:
                            table_tabs = st.tabs([f"📊 {name}" for name in tables.keys()])
                            
                            for tab_idx, (table_name, table_data) in enumerate(tables.items()):
                                with table_tabs[tab_idx]:
                                    df = pd.DataFrame(table_data)
                                    # Clean the DataFrame by removing all-null columns
                                    df_cleaned = clean_dataframe(df)
                                    st.dataframe(
                                        df_cleaned,
                                        use_container_width=True,
                                        height=min(400, (len(df_cleaned) + 1) * 35 + 3),
                                        hide_index=True
                                    )
                                    
                                    # Add download button
                                    csv = df.to_csv(index=False).encode('utf-8')
                                    st.download_button(
                                        label="📥 Download CSV",
                                        data=csv,
                                        file_name=f"{file_data['file_name'].rsplit('.', 1)[0]}_{sheet_name}_{table_name}.csv",
                                        mime='text/csv',
                                        key=f"download_{file_data['id']}_{sheet_name}_{table_name}",
                                        use_container_width=True
                                    )
                                    
                                    # Inline chat interface
                                    st.markdown("---")
                                    st.subheader("💬 Chat with this Table")
                                    
                                    # Create a unique key for this chat
                                    chat_key = f"browse_{file_data['id']}_{sheet_name}_{table_name}"
                                    
                                    # Initialize chat messages if not exists
                                    if chat_key not in st.session_state.chat_messages:
                                        st.session_state.chat_messages[chat_key] = [
                                            {"role": "assistant", "content": f"Ask me anything about this table: {table_name}"}
                                        ]
                                    
                                    # Display chat messages
                                    for msg in st.session_state.chat_messages[chat_key]:
                                        with st.chat_message(msg["role"]):
                                            st.write(msg["content"])
                                    
                                    # Chat input with a fixed key
                                    if prompt := st.chat_input("Ask about this table...", key=f"chat_input_{chat_key}"):
                                        with st.spinner("Analyzing table..."):
                                            # Add user message
                                            st.session_state.chat_messages[chat_key].append(
                                                {"role": "user", "content": prompt}
                                            )
                                            
                                            # Generate AI response with table context
                                            response = analyze_table(
                                                df_cleaned,
                                                f"{prompt} - Answer based on this table: {table_name} in sheet: {sheet_name}"
                                            )
                                            
                                            # Add assistant response
                                            st.session_state.chat_messages[chat_key].append(
                                                {"role": "assistant", "content": response}
                                            )
                                            st.rerun()
                        else:
                            st.info("No tables found in this sheet.")
            else:
                st.warning("No sheets with tables found in this file.")
            
            # Add some space before the back button
            st.markdown("")
            if st.button("← Back to All Files", key="back_to_files_btn"):
                st.session_state.viewing_file_id = None
                st.rerun()
            return
    
    # If we get here, show the file list
    st.title("📋 Browse Excel Files")
    
    # Get files from database
    files = db.list_excel_files()
    
    if not files:
        st.info("No Excel files found. Upload a file to get started!")
    else:
        st.subheader(f"Found {len(files)} files")
        
        # Display files in a list with actions
        for file in files:
            # Format the datetime for display
            uploaded_at = file['uploaded_at']
            if hasattr(uploaded_at, 'strftime'):
                formatted_date = uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                formatted_date = str(uploaded_at)
                
            with st.expander(f"📄 {file['file_name']} - {formatted_date}"):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**Tables:** {file['tables_count']}")
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{file['id']}", type="primary"):
                        st.session_state.delete_file_id = file['id']
                
                if st.button("View Tables", key=f"view_{file['id']}"):
                    # Clear any existing chat state
                    if 'chat_file_id' in st.session_state:
                        del st.session_state['chat_file_id']
                    
                    # Set viewing state
                    st.session_state.viewing_file_id = file['id']
                    st.session_state.page = 'file_detail'
                    st.rerun()
        
        # Handle file deletion with confirmation dialog
        if 'delete_file_id' in st.session_state and st.session_state.delete_file_id:
            file_id = st.session_state.delete_file_id
            file_to_delete = next((f for f in files if f['id'] == file_id), None)
            
            if file_to_delete:
                # Create a modal dialog for confirmation
                with st.sidebar:
                    st.warning("⚠️ Confirm Deletion")
                    st.write(f"You are about to delete: **{file_to_delete['file_name']}**")
                    st.write("This action cannot be undone.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm Delete", key=f"confirm_delete_{file_id}", type="primary"):
                            success, message = db.delete_excel_file(file_id)
                            if success:
                                st.success(message)
                                # Clear the selected file if it was deleted
                                if st.session_state.get('selected_file_id') == file_id:
                                    st.session_state.selected_file_id = None
                                # Clear the delete state and rerun to update the UI
                                del st.session_state.delete_file_id
                                st.rerun()
                            else:
                                st.error(message)
                    
                    with col2:
                        if st.button("❌ Cancel", key=f"cancel_delete_{file_id}"):
                            del st.session_state.delete_file_id
                            st.rerun()

def show_file_detail_page():
    """Render the file detail page."""
    # Clear any chat state when entering file detail view
    if 'chat_file_id' in st.session_state:
        del st.session_state['chat_file_id']
    
    if 'viewing_file_id' not in st.session_state:
        st.warning("No file selected")
        st.session_state.page = 'browse'
        st.rerun()
        return
    
    try:
        file_data = db.get_excel_file(st.session_state.viewing_file_id)
        if not file_data:
            st.error("File not found")
            del st.session_state.viewing_file_id
            st.session_state.page = 'browse'
            st.rerun()
            return
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        if 'viewing_file_id' in st.session_state:
            del st.session_state.viewing_file_id
        st.session_state.page = 'browse'
        st.rerun()
        return
    
    # Create two columns for better layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title(f"📄 {file_data['file_name']}")
    with col2:
        if st.button("← Back to Files", use_container_width=True):
            # Clear viewing state when going back
            if 'viewing_file_id' in st.session_state:
                del st.session_state.viewing_file_id
            st.session_state.page = 'browse'
            st.rerun()
    
    st.caption(f"Uploaded: {file_data['uploaded_at']}")
    
    # Add tabs for sheets
    if file_data['tables']:
        sheet_names = list(file_data['tables'].keys())
        tabs = st.tabs([f"📑 {name}" for name in sheet_names])
        
        for idx, (sheet_name, tables) in enumerate(file_data['tables'].items()):
            with tabs[idx]:
                st.subheader(f"{sheet_name}")
                
                # Create tabs for tables within each sheet
                if tables:
                    table_tabs = st.tabs([f"📊 {name}" for name in tables.keys()])
                    
                    for tab_idx, (table_name, table_data) in enumerate(tables.items()):
                        with table_tabs[tab_idx]:
                            # Convert all data to strings to avoid Arrow type conflicts
                            df = pd.DataFrame(table_data)
                            
                            # Ensure all values are strings to prevent Arrow type conflicts
                            df = df.astype(str)
                            
                            # Clean the dataframe
                            df_cleaned = clean_dataframe(df)
                            
                            # Display the dataframe with improved styling
                            st.dataframe(
                                df_cleaned,
                                use_container_width=True,
                                height=min(400, (len(df_cleaned) + 1) * 35 + 3),
                                hide_index=True,
                            )
                            
                            # Add download, duplicate and back buttons
                            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                            with col1:
                                # Add a download button for the entire file
                                with open(file_data['file_path'], 'rb') as f:
                                    st.download_button(
                                        label="⬇️ Download",
                                        data=f,
                                        file_name=file_data['file_name'],
                                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                        use_container_width=True,
                                        help="Download this file"
                                    )
                            with col2:
                                if st.button("⎘ Duplicate", use_container_width=True, 
                                           help="Create a copy of this file with a new number"):
                                    success, message, new_file_id = db.duplicate_excel_file(file_data['id'])
                                    if success:
                                        st.success(message)
                                        # Optionally redirect to the new file
                                        # st.session_state.viewing_file_id = new_file_id
                                    else:
                                        st.error(message)
                                    st.rerun()
                            with col3:
                                if st.button("← Back to Files", use_container_width=True, 
                                           help="Return to file browser"):
                                    del st.session_state.viewing_file_id
                                    st.rerun()
    else:
        st.warning("No sheets with tables found in this file.")

def show_chat_page():
    """Render the chat interface page."""
    st.title("💬 Chat with Tables")
    
    if not st.session_state.get('selected_file_id'):
        st.warning("Please select a file first")
        st.session_state.page = 'browse'
        st.rerun()
        return
    
    # Get file data
    file_data = db.get_excel_file(st.session_state.selected_file_id)
    if not file_data:
        st.error("File not found")
        st.session_state.page = 'browse'
        st.rerun()
        return
    
    # Initialize chat history if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Ask me anything about the data in {file_data['file_name']}."}
        ]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Simple response for now - can be enhanced with LLM integration
            if any(word in prompt.lower() for word in ['hello', 'hi', 'hey']):
                response = "Hello! How can I help you with this data today?"
            elif 'row count' in prompt.lower() or 'number of rows' in prompt.lower():
                total_rows = sum(len(table) for tables in file_data['tables'].values() for table in tables.values())
                response = f"The file contains a total of {total_rows} rows across all tables."
            elif 'columns' in prompt.lower() or 'fields' in prompt.lower():
                all_columns = set()
                for tables in file_data['tables'].values():
                    for table in tables.values():
                        if table:
                            all_columns.update(table[0].keys())
                response = f"The file contains these columns: {', '.join(all_columns)}"
            else:
                response = "I can help you analyze this data. Try asking about the number of rows, columns, or specific values in the tables."
            
            # Simulate stream of response
            for chunk in response.split():
                full_response += chunk + " "
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.05)
            
            message_placeholder.markdown(full_response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # Add a back button at the bottom
    if st.button("← Back to Files", use_container_width=True):
        st.session_state.page = 'browse'
        st.rerun()

# Navigation
st.sidebar.title("📊 Excel ChatBot")
page = st.sidebar.radio(
    "Navigation",
    ["📤 Upload Excel", "📋 Browse Files", "💬 Chat with Tables"],
    index=0 if st.session_state.page == 'upload' else 1 if st.session_state.page == 'browse' else 2
)

# Page routing
if page == "📤 Upload Excel":
    st.session_state.page = 'upload'
    show_upload_page()
elif page == "📋 Browse Files":
    st.session_state.page = 'browse'
    show_browse_page()
elif page == "💬 Chat with Tables":
    st.session_state.page = 'chat'
    show_chat_page()

# Clear upload success state when navigating away from upload page
if 'last_page' in st.session_state and st.session_state.last_page == 'upload' and st.session_state.page != 'upload':
    st.session_state.upload_success = False

# Store current page for next render
st.session_state.last_page = st.session_state.page

# Handle file detail page (not in sidebar)
if st.session_state.page == 'file_detail':
    show_file_detail_page()
