import streamlit as st
import os
import re
import tarfile
import tempfile
import json
from collections import defaultdict
import time
from datetime import datetime
from itertools import chain

# === Paths base directory ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === Load users ===
def load_users():
    users_path = os.path.join(BASE_DIR, "database", "users.json")
    with open(users_path, "r", encoding="utf-8") as f:
        return json.load(f)

# === Authentication ===
def authenticate(username, password):
    users = load_users()

    if username not in users:
        return None

    user = users[username]

    if user.get("password") != password:
        return None

    try:
        expiry = datetime.strptime(user["expires"], "%Y-%m-%d")
        if expiry < datetime.today():
            return None
    except:
        return None

    return True

# === Collect models ===
def get_models(problems_database):
    model_set = set(chain.from_iterable(
        v.get("modelo", []) for v in problems_database.values() if isinstance(v.get("modelo"), list)
    ))
    return ['All'] + sorted(model_set)

# === Login Painel ===
def login_screen():
    logo_path = os.path.join(BASE_DIR, "images", "mindray_logo_transparent.png")
    st.image(logo_path, width=150)
    st.markdown("## 🔐 Endo Service Platform - Login")
    st.markdown("Please enter your credentials to access the platform.")
    st.markdown("---")

    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    if st.button("Login"):
        if authenticate(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Access denied. Invalid user, password, or expired license.")

# === Login control ===
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login_screen()
    st.stop()

# === Home Config ===
st.set_page_config(page_title="Endo Service Platform", layout="wide")
logo_path = os.path.join(BASE_DIR, "images", "mindray_logo_transparent.png")
st.image(logo_path, width=150)

# === Database ===
if "problems_database" not in st.session_state:
    problems_path = os.path.join(BASE_DIR, "database", "problems_database.json")
    with open(problems_path, "r", encoding="utf-8") as f:
        st.session_state.problems_database = json.load(f)

problems_database = st.session_state.problems_database

# === Tabs ===
if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = "Log Analyzer"

menu = ["Log Analyzer", "Search Errors"]

selected_tab = st.sidebar.radio(
    "Navigation",
    menu,
    index=menu.index(st.session_state.selected_tab)
)

if selected_tab != st.session_state.selected_tab:
    st.session_state.selected_tab = selected_tab
    st.rerun()

# === Logout ===
with st.sidebar:
    if st.button("🔲 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state["logged_in"] = False
        st.rerun()

# === Log Analyzer ===
def run_log_analyzer():
    st.markdown("### 📌 How to Prepare the Log File")
    st.info("""
The log file exported from the equipment is in `.lzo` format.

Steps:
1. Copy the `.lzo` file.
2. Run `Converter_LZO.bat`.
3. It generates a `.tar` file.
4. Upload it here.

If you don't have the converter, contact Mindray Technical Support.
    """)

    uploaded_file = st.file_uploader("Select a .tar log file", type=["tar"])
    progress_bar = st.progress(0, text="Waiting for file...")

    def extract_tar(file):
        temp_dir = tempfile.mkdtemp()
        tar_path = os.path.join(temp_dir, file.name)
        with open(tar_path, "wb") as f:
            f.write(file.getbuffer())
        with tarfile.open(tar_path, "r") as tar:
            tar.extractall(temp_dir)
        return [os.path.join(root, f) for root, _, files in os.walk(temp_dir) for f in files if f.endswith((".log", ".txt"))]

    def extract_keyword_and_code_errors(log_files):
        keywords = ["alarm", "timeout", "error", "contamination", "heating", "heat", "fail", "failure"]
        grouped = defaultdict(lambda: defaultdict(lambda: {"count": 0, "last_timestamp": ""}))
        code_pattern = re.compile(r"\b(E\d{3})\b", re.IGNORECASE)
        timestamp_pattern = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{1,2}:\d{1,2}")

        for file in log_files:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    clean_line = line.strip()
                    lower_line = clean_line.lower()

                    # Takes the most recent timestamp in the line, if any
                    ts_match = timestamp_pattern.search(clean_line)
                    timestamp = ts_match.group(0) if ts_match else ""

                    # Verificação por palavra-chave
                    for keyword in keywords:
                        if keyword in lower_line:
                            entry = grouped[keyword.upper()][clean_line]
                            entry["count"] += 1
                            if timestamp > entry["last_timestamp"]:
                                entry["last_timestamp"] = timestamp
                            break

                    # Verify by code E###
                    match = code_pattern.search(clean_line)
                    if match:
                        code = match.group(1).upper()
                        entry = grouped[code][clean_line]
                        entry["count"] += 1
                        if timestamp > entry["last_timestamp"]:
                            entry["last_timestamp"] = timestamp

        return grouped


    if uploaded_file:
        progress_bar = st.progress(0, text="⏳ Extracting .tar file...")

        with st.spinner("Extracting file..."):
            try:
                log_files = extract_tar(uploaded_file)
                progress_bar.progress(50, text=f"✅ Extracted {len(log_files)} log files. Starting analysis...")

                # Agora começa a análise
                grouped_errors = extract_keyword_and_code_errors(log_files)
                progress_bar.progress(100, text="✅ Analysis complete.")
                st.success(f"Extracted {len(log_files)} log files.")

                if grouped_errors:
                    st.subheader("⚠️ Errors Found in Logs")

                    for error, lines_dict in sorted(grouped_errors.items(), key=lambda x: sum(v["count"] for v in x[1].values()), reverse=True):
                        total_count = sum(data["count"] for data in lines_dict.values())
                        with st.expander(f"🔹 {error} — {total_count} occurrence(s)"):
                            sorted_lines = sorted(lines_dict.items(), key=lambda x: x[1]["count"], reverse=True)
                            for line_text, data in sorted_lines:
                                last_ts = data["last_timestamp"] if data["last_timestamp"] else "No timestamp"
                                st.markdown(f"""<span style='color:#AAAAAA;'>• {last_ts} — "{line_text}" ({data['count']}x)</span>""", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"An error occurred: {e}")

# === Search Errors ===
def run_error_search():
    st.subheader("🔍 Search Errors")
    query = st.session_state.get("search_query", "")
    st.text_input("Enter a keyword (e.g., 'contamination')", value=query, key="search_query_input")

    # Performs search automatically if it comes from Log Analyzer
    if query and "results" not in st.session_state:
        search_clicked = True

    models = get_models(problems_database)
    selected_model = st.radio("📌 Filter by Equipment Model", models, horizontal=True)

    col_left, col_spacer, col_right = st.columns([1, 8, 1])
    with col_left:
        search_clicked = st.button("Search")
    with col_right:
        clear_clicked = st.button("Clear")

    if clear_clicked:
        st.session_state.pop("query", None)
        st.session_state.pop("results", None)
        st.session_state.pop("selected_error", None)
        st.session_state.selected_tab = "Search Errors"
        st.rerun()

    if search_clicked:
        st.session_state.results = {}
        for key, value in problems_database.items():
            matches_keyword = (
                not query
                or query.lower() in key.lower()
                or query.lower() in value['problem'].lower()
                or any(query.lower() in cause.lower() for cause in value['causes'])
            )
            matches_model = (
                selected_model == "All"
                or (isinstance(value.get("modelo"), list) and selected_model in value["modelo"])
            )
            if matches_keyword and matches_model:
                st.session_state.results[key] = value

        if "results" in st.session_state and st.session_state.results:
            for category, data in st.session_state.results.items():
                if "selected_error" not in st.session_state:
                    st.session_state.selected_error = category

                expanded = st.session_state.selected_error == category
                with st.expander(f"🔧 {category}", expanded=expanded):
                    st.session_state.selected_error = category

                    st.markdown(f"**Problem:** {data['problem']}")
                    if "modelo" in data:
                        st.markdown(f"**Applicable Models:** {', '.join(data['modelo'])}")

                    image_file = data.get("image")
                    image_path = os.path.join(BASE_DIR, "images", image_file) if image_file else None
                    if image_path and os.path.isfile(image_path):
                        st.image(image_path, caption="Associated image", width=300)

                    st.markdown("**Causes:**")
                    for c in data['causes']:
                        st.markdown(f"- {c}")

                    st.markdown("**Recommended Actions:**")
                    for r in data['repairs']:
                        st.markdown(f"- {r}")

                    safe_name = re.sub(r'[^\w\s-]', '', category).strip()
                    pptx_path = os.path.join(BASE_DIR, "resources", f"{safe_name}.pptx")
                    if os.path.isfile(pptx_path):
                        with open(pptx_path, "rb") as f:
                            st.download_button(
                                label="📥 Download Instructions (.pptx)",
                                data=f,
                                file_name=f"{safe_name}.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                key=f"download_{safe_name}"
                            )
                    else:
                        st.warning("⚠️ Troubleshooting guide not available.")
        else:
            st.info("No results found.")

# === Routing ===
if st.session_state.selected_tab == "Log Analyzer":
    run_log_analyzer()
elif st.session_state.selected_tab == "Search Errors":
    run_error_search()