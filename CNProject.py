import streamlit as st
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import os
import threading
from datetime import datetime
import shutil
import requests
from pathlib import Path
import time
import humanize
from urllib.parse import quote, unquote
import logging
from streamlit_extras.colored_header import colored_header
from streamlit_modal import Modal
import extra_streamlit_components as stx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state variables
if 'server_running' not in st.session_state:
    st.session_state.server_running = False
if 'transfer_history' not in st.session_state:
    st.session_state.transfer_history = []


# styling with custom CSS
def load_custom_css():
    st.markdown("""
        <style>
        /* Main container styling */
        .main {
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
            margin-bottom: 2rem;
        }

        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding: 0 24px;
            background-color: #f8f9fa;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background-color: #e9ecef;
        }

        .stTabs [aria-selected="true"] {
            background-color: #2962ff !important;
            color: white !important;
        }

        /* Button styling */
        .custom-button {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            background-color: #2962ff;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .custom-button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .custom-button.danger {
            background-color: #dc3545;
        }

        /* File box styling */
        .file-box {
            background-color: #ffffff;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            border: 1px solid #e9ecef;
            transition: all 0.2s ease;
        }

        .file-box:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        /* Status indicators */
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .status-success {
            background-color: #28a74520;
            color: #28a745;
        }

        .status-failed {
            background-color: #dc354520;
            color: #dc3545;
        }

        /* Server status indicator */
        .server-status {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }

        .server-status.running {
            background-color: #28a74520;
            color: #28a745;
        }

        .server-status.stopped {
            background-color: #dc354520;
            color: #dc3545;
        }
        </style>
    """, unsafe_allow_html=True)


def save_transfer_history(action, filename, status, url=""):
    st.session_state.transfer_history.append({
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'action': action,
        'filename': filename,
        'status': status,
        'url': url
    })


def clear_transfer_history():
    st.session_state.transfer_history = []


def delete_file(filepath):
    try:
        os.remove(filepath)
        save_transfer_history("delete", filepath.name, "success")
        return True
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        save_transfer_history("delete", filepath.name, "failed")
        return False


class SimpleFileHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

                html = """
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Upload File</h2>
                    <form action="/upload" method="POST" enctype="multipart/form-data">
                        <input type="file" name="file" style="margin: 10px 0;">
                        <input type="submit" value="Upload" style="padding: 5px 15px; background-color: #2962ff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    </form>
                </body>
                </html>
                """
                self.wfile.write(html.encode())

            elif self.path.startswith('/downloads/'):
                filename = unquote(self.path[10:])
                filepath = os.path.join('downloads', filename)

                if os.path.exists(filepath):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.end_headers()

                    with open(filepath, 'rb') as file:
                        shutil.copyfileobj(file, self.wfile)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'File not found')

        except Exception as e:
            logger.error(f"Error in GET handler: {str(e)}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal server error')

    def do_POST(self):
        try:
            if self.path == '/upload':
                content_type = self.headers['Content-Type']
                if not content_type or not content_type.startswith('multipart/form-data'):
                    self.send_response(400)
                    self.end_headers()
                    return

                content_length = int(self.headers['Content-Length'])
                file_data = self.rfile.read(content_length)

                filename = f"uploaded_file_{int(time.time())}"
                filepath = os.path.join('downloads', filename)

                with open(filepath, 'wb') as f:
                    f.write(file_data)

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'File uploaded successfully')

        except Exception as e:
            logger.error(f"Error in POST handler: {str(e)}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal server error')


class FileTransferApp:
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        self.server_thread = None
        os.makedirs('downloads', exist_ok=True)

    def start_server(self):
        try:
            handler = SimpleFileHandler
            self.server = socketserver.TCPServer(("0.0.0.0", self.port), handler)
            logger.info(f"Server started on port {self.port}")
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Server error: {str(e)}")

    def stop_server(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Server stopped")


def create_ui():
    st.set_page_config(
        page_title="File Transfer",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    load_custom_css()

    # Initialize session state
    if 'app' not in st.session_state:
        st.session_state.app = FileTransferApp()

    # Page Header
    colored_header(
        label="File Transfer",
        description="Secure and easy file sharing",
        color_name="blue-70"
    )

    # Sidebar with styling
    with st.sidebar:
        st.markdown("### ⚙️ Server Settings")

        # Server status indicator
        status_class = "running" if st.session_state.server_running else "stopped"
        status_icon = "🟢" if st.session_state.server_running else "🔴"
        st.markdown(
            f"""<div class="server-status {status_class}">
                {status_icon} Server {status_class.title()}
            </div>""",
            unsafe_allow_html=True
        )

        port = st.number_input("Port Number", value=8000, min_value=1024, max_value=65535)

        if not st.session_state.server_running:
            if st.button("🚀 Start Server", key="start_server", type="primary"):
                try:
                    st.session_state.app = FileTransferApp(port=port)
                    st.session_state.server_thread = threading.Thread(
                        target=st.session_state.app.start_server,
                        daemon=True
                    )
                    st.session_state.server_thread.start()
                    st.session_state.server_running = True
                    st.success("✅ Server started successfully!")
                except Exception as e:
                    st.error(f"❌ Failed to start server: {str(e)}")
        else:
            if st.button("⏹️ Stop Server", key="stop_server", type="secondary"):
                try:
                    st.session_state.app.stop_server()
                    st.session_state.server_running = False
                    st.warning("Server stopped!")
                except Exception as e:
                    st.error(f"Failed to stop server: {str(e)}")

    # Main content with tabs
    tab1, tab2, tab3 = st.tabs([
        "📤 Send Files",
        "📥 Receive Files",
        "📋 Transfer History"
    ])

    with tab1:
        st.markdown("### 📤 Send Files")
        receiver_url = st.text_input("🌐 Receiver's URL", placeholder="http://192.168.1.100:8000")
        uploaded_file = st.file_uploader("📎 Choose file to send", type=None)

        if uploaded_file and receiver_url:
            if st.button("📤 Send File", key="send_file", type="primary"):
                with st.spinner("📡 Sending file..."):
                    try:
                        files = {'file': uploaded_file.getvalue()}
                        response = requests.post(f"{receiver_url}/upload", files=files)

                        if response.status_code == 200:
                            st.success("✅ File sent successfully!")
                            save_transfer_history("send", uploaded_file.name, "success", receiver_url)
                        else:
                            st.error(f"❌ Failed to send file: {response.text}")
                            save_transfer_history("send", uploaded_file.name, "failed", receiver_url)
                    except Exception as e:
                        st.error(f"❌ Error sending file: {str(e)}")
                        save_transfer_history("send", uploaded_file.name, "failed", receiver_url)

    with tab2:
        st.markdown("### 📥 Receive Files")

        if not st.session_state.server_running:
            st.warning("⚠️ Server is not running. Start the server to receive files.")
        else:
            st.success("✅ Server is running and ready to receive files!")

            st.markdown("#### 📚 Received Files")
            received_files = sorted(
                Path("downloads").glob("*"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            if received_files:
                for file_path in received_files:
                    stats = file_path.stat()
                    with st.container():
                        st.markdown('<div class="file-box">', unsafe_allow_html=True)
                        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                        with col1:
                            st.markdown(f"📄 **{file_path.name}**")
                        with col2:
                            st.text(f"📊 Size: {humanize.naturalsize(stats.st_size)}")
                        with col3:
                            with open(file_path, "rb") as f:
                                st.download_button(
                                    "⬇️ Download",
                                    f,
                                    file_name=file_path.name,
                                    mime="application/octet-stream",
                                    key=f"download_{file_path.name}"
                                )
                        with col4:
                            if st.button("🗑️ Delete", key=f"delete_{file_path.name}", type="secondary"):
                                if delete_file(file_path):
                                    st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("📭 No files received yet")

    with tab3:
        st.markdown("### 📋 Transfer History")

        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("🗑️ Clear History", key="clear_history", type="secondary"):
                clear_transfer_history()
                st.rerun()

        if st.session_state.transfer_history:
            for entry in reversed(st.session_state.transfer_history):
                with st.container():
                    st.markdown('<div class="history-box">', unsafe_allow_html=True)
                    cols = st.columns([2, 2, 2, 2, 3])

                    with cols[0]:
                        st.markdown(f"🕒 **{entry['timestamp']}**")
                    with cols[1]:
                        action_icons = {
                            "send": "📤",
                            "receive": "📥",
                            "delete": "🗑️"
                        }
                        st.markdown(f"{action_icons.get(entry['action'], '➡️')} **{entry['action'].title()}**")
                    with cols[2]:
                        status_icon = "✅" if entry['status'] == "success" else "❌"
                        status_class = "status-success" if entry['status'] == "success" else "status-failed"
                        st.markdown(
                            f"""<span class="status-badge {status_class}">
                                {status_icon} {entry['status'].title()}
                            </span>""",
                            unsafe_allow_html=True
                        )
                    with cols[3]:
                        st.markdown(f"📄 **{entry['filename']}**")
                    with cols[4]:
                        if entry['url']:
                            st.markdown(f"🌐 `{entry['url']}`")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("📭 No transfer history available")


if __name__ == "__main__":
    create_ui()