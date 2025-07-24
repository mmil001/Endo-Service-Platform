import streamlit as st
import os
import tarfile
import tempfile
import json
import re
import time
from datetime import datetime
from collections import defaultdict
from itertools import chain

# === Diretório base ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === Carregar dados ===
def load_users():
    path = os.path.join(BASE_DIR, "database", "users.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_patterns():
    path = os.path.join(BASE_DIR, "database", "patterns.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_problems():
    path = os.path.join(BASE_DIR, "database", "problems_database.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# === Autenticação ===
def authenticate(username, password):
    users = load_users()
    user = users.get(username)
    if not user or user["password"] != password:
        return False
    try:
        expiry = datetime.strptime(user["expires"], "%Y-%m-%d")
        return expiry >= datetime.today()
    except:
        return False

# === Login ===
def login_screen():
    logo_path = os.path.join(BASE_DIR, "images", "mindray_logo_transparent.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    st.title("🔐 Endo Service Platform - Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Access denied. Invalid user, password, or expired license.")

# === Controle de sessão ===
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    login_screen()
    st.stop()

# === Dados ===
patterns = load_patterns()
problems = load_problems()

# === Layout ===
st.set_page_config("Endo Service Platform", layout="wide")
logo_path = os.path.join(BASE_DIR, "images", "mindray_logo_transparent.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=150)
menu = st.sidebar.radio("Navigation", ["Log Analyzer", "Search Errors"])
if st.sidebar.button("🔲 Logout"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# === Funções ===
def extract_tar(file):
    temp_dir = tempfile.mkdtemp()
    tar_path = os.path.join(temp_dir, file.name)
    with open(tar_path, "wb") as f:
        f.write(file.getbuffer())
    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(temp_dir)
    return [os.path.join(root, name) for root, _, files in os.walk(temp_dir) for name in files if name.endswith(('.log', '.txt'))]

def analyze_logs(log_files):
    found = defaultdict(list)
    seen_errors = set()
    for file in log_files:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                clean = line.strip()
                if clean and clean not in seen_errors and re.search(r"[a-zA-Z]", clean):
                    for key, pat in patterns.items():
                        if re.search(pat, clean, re.IGNORECASE):
                            found[key].append(1)  # count only
                            seen_errors.add(clean)
                            break
    return found

def render_problem(category):
    data = problems.get(category)
    if not data:
        return
    with st.expander(f"🔧 {category}", expanded=True):
        st.markdown(f"**Problem:** {data.get('problem', 'N/A')}")
        if data.get("model"):
            st.markdown(f"**Applicable Models:** {', '.join(data['model'])}")
        if data.get("causes"):
            st.markdown("**Causes:**")
            for c in data["causes"]:
                st.markdown(f"- {c}")
        if data.get("solutions"):
            st.markdown("**Solutions:**")
            for s in data["solutions"]:
                st.markdown(f"- {s}")
        if data.get("manual_reference"):
            st.markdown(f"**Manual Reference:** {data['manual_reference']}")
        if data.get("image"):
            img_path = os.path.join(BASE_DIR, "images", data["image"])
            if os.path.exists(img_path):
                st.image(img_path, width=300)
        if isinstance(data.get("Troubleshooting Guide"), str):
            pptx_path = os.path.join(BASE_DIR, "resources", data["Troubleshooting Guide"])
            if os.path.exists(pptx_path):
                with open(pptx_path, "rb") as f:
                    st.download_button("📥 Download Guide", data=f, file_name=data["Troubleshooting Guide"], mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

# === Aba Log Analyzer ===
if menu == "Log Analyzer":
    st.header("📂 Log Analyzer")
    st.info("Upload a `.tar` file exported from equipment logs.")
    uploaded_file = st.file_uploader("Upload `.tar` file", type=["tar"])
    if uploaded_file:
        with st.spinner("Analyzing..."):
            try:
                log_files = extract_tar(uploaded_file)
                result = analyze_logs(log_files)
                matched_keys = [key for key in result if key in problems]
                if matched_keys:
                    for key in matched_keys:
                        render_problem(key)
                else:
                    st.success("✅ No known errors found.")
            except Exception as e:
                st.error(f"Error during analysis: {e}")

# === Aba Search Errors ===
elif menu == "Search Errors":
    st.header("🔍 Search Errors")
    query = st.text_input("Enter keyword")
    all_models = sorted(set(chain.from_iterable(v.get("model", []) for v in problems.values() if isinstance(v.get("model"), list))))
    selected_model = st.selectbox("Filter by model", ["All"] + all_models)

    if st.button("Search"):
        results = {}
        for k, v in problems.items():
            if query.lower() in k.lower() or query.lower() in json.dumps(v).lower():
                if selected_model == "All" or selected_model in v.get("model", []):
                    results[k] = v
        if results:
            for key in results:
                render_problem(key)
        else:
            st.warning("No results found.")
