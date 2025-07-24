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

# === Carrega usuários ===
def load_users():
    users_path = os.path.join(BASE_DIR, "database", "users.json")
    with open(users_path, "r", encoding="utf-8") as f:
        return json.load(f)

# === Autenticação ===
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

# === Coletar modelos ===
def get_models(problems_database):
    model_set = set(chain.from_iterable(
        v.get("model", []) for v in problems_database.values() if isinstance(v.get("model"), list)
    ))
    return ['All'] + sorted(model_set)

# === Tela de login ===
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

# === Controle de login ===
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login_screen()
    st.stop()

# === Config inicial ===
st.set_page_config(page_title="Endo Service Platform", layout="wide")
logo_path = os.path.join(BASE_DIR, "images", "mindray_logo_transparent.png")
st.image(logo_path, width=150)

# === Banco de erros ===
if "problems_database" not in st.session_state:
    problems_path = os.path.join(BASE_DIR, "database", "problems_database.json")
    with open(problems_path, "r", encoding="utf-8") as f:
        st.session_state.problems_database = json.load(f)

problems_database = st.session_state.problems_database

# === Patterns (fixos ou pode carregar do JSON depois) ===
patterns = {
    "Contamination Detected": r"(contamin|liquid.*detected|inlet.*liquid|pollution.*mark|level sensor error|ERR#08)",
    "Communication Errors": r"(connect.*failed|network.*unreach|ipc.*fail|timeout|socket.*error)",
    "Heating Errors": r"(heat.*fail|temperature.*alarm|ERR#14|ERR#15|heating plate|tube.*fail)",
    "Insufflator Errors": r"(flow.*error|pressure.*fail|valve.*fail|ERR#04|gas leak|pinch.*valve)",
    "Insufflation / Flow Errors": r"(proportional valve|zero drift|ERR#0[4-9]|ERR#1[0-2])",
    "Power Supply Errors": r"(power.*fail|fuse.*blown|voltage.*error|ERR#06|no power)",
    "Image Processor / Camera Errors": r"(video.*lost|camera.*error|CCU.*fail|no signal|image.*not found|firmware.*error|hdmi|dvi|sdi.*fail)",
    "Camera Head Errors": r"(camera head.*error|optical.*fail|coupler|lens|focus.*fail|zoom.*fail|no.*camera.*input)",
    "Video Recording / USB Errors": r"(usb.*fail|record.*error|video.*not saved|no.*recording|file.*system.*error)"
}

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

    def analyze_logs(log_files):
        seen = set()
        all_lines = []
        total_files = len(log_files)
        for idx, file in enumerate(log_files):
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    clean = line.strip()
                    if clean and clean not in seen and re.search(r"[a-zA-Z]", clean):
                        all_lines.append(clean)
                        seen.add(clean)
            progress = int(((idx + 1) / total_files) * 50)
            progress_bar.progress(progress, text=f"Reading logs... ({progress}%)")
            time.sleep(0.05)

        # NOVO: tenta casar com nomes exatos do problems_database
        found_issues = {}
        def analyze_logs(log_files):
            seen = set()
            all_lines = []
            total_files = len(log_files)
            
            for idx, file in enumerate(log_files):
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        clean = line.strip()
                        if clean and clean not in seen and re.search(r"[a-zA-Z]", clean):
                            all_lines.append(clean)
                            seen.add(clean)

                progress = int(((idx + 1) / total_files) * 50)
                progress_bar.progress(progress, text=f"Reading logs... ({progress}%)")
                time.sleep(0.05)

            # Identificar padrões nos logs com base em patterns
            found_issues = defaultdict(list)

            for line in all_lines:
                for key, pattern in patterns.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        found_issues[key].append(line)

            progress_bar.progress(100, text="✅ Analysis complete.")
            return found_issues

    if uploaded_file:
        with st.spinner("Extracting file..."):
            try:
                log_files = extract_tar(uploaded_file)
                st.success(f"Extracted {len(log_files)} log files.")
                issues = analyze_logs(log_files)
            except Exception as e:
                st.error(f"An error occurred while reading logs: {e}")
            return

        if issues:
            st.subheader("⚠️ Diagnosed Issues")
            for key, log_lines in issues.items():
                data = problems_database.get(key)
                with st.expander(f"🔧 {key}", expanded=True):
                    for line in log_lines:
                        st.markdown(f"**Log Line:** `{line}`")

                    if data:
                        st.markdown(f"**Problem:** {data.get('problem', 'N/A')}")
                        st.markdown(f"**Applicable Models:** {', '.join(data.get('model', []))}")

                        # Mostrar imagem
                        image_file = data.get("image")
                        if image_file:
                            image_path = os.path.join(BASE_DIR, "images", image_file)
                            if os.path.isfile(image_path):
                                st.image(image_path, caption="Associated image", width=300)

                        # Mostrar causas
                        causes = data.get("causes", [])
                        if isinstance(causes, list) and causes:
                            st.markdown("**Causes:**")
                            for c in causes:
                                st.markdown(f"- {c}")

                        # Mostrar soluções
                        solutions = data.get("solutions", [])
                        if isinstance(solutions, list) and solutions:
                            st.markdown("**Recommended Actions:**")
                            for s in solutions:
                                st.markdown(f"- {s}")

                        # Referência de manual
                        manual = data.get("manual_reference")
                        if manual:
                            st.markdown(f"**Manual Reference:** {manual}")

                            # Mostrar troubleshooting guide (PPT)
                            ppt_file = data.get("Troubleshooting Guide")
                            if ppt_file:
                                ppt_path = os.path.join(BASE_DIR, "resources", ppt_file)
                                if os.path.isfile(ppt_path):
                                    with open(ppt_path, "rb") as f:
                                        st.download_button(
                                            label="📥 Download Instructions (.pptx)",
                                            data=f,
                                            file_name=ppt_file,
                                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                            key=f"ppt_{ppt_file}_{time.time()}"
                                        )
                                else:
                                    st.warning("⚠️ Troubleshooting guide file not found.")

                    else:
                        st.warning("⚠️ No data found in problem database.")
        else:
            st.info("✅ No issues matched from the log.")

# === Search Errors ===
def run_error_search():
    st.subheader("🔍 Search Errors")
    query = st.text_input("Enter a keyword (e.g., 'contamination')")

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
                or query.lower() in key.lower()
            )  

            matches_model = (
                selected_model == "All"
                or (isinstance(value.get("model"), list) and selected_model in value["model"])
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

                    st.markdown(f"**Problem:** {category}")
                    if "model" in data:
                        st.markdown(f"**Applicable Models:** {', '.join(data['model'])}")

                    image_file = data.get("image")
                    image_path = os.path.join(BASE_DIR,  "images", image_file) if image_file else None
                    if image_path and os.path.isfile(image_path):
                        st.image(image_path, caption="Associated image", width=300)

                    # === Causas ===
                    cause_keys = ["causes", "Causes", "Possible Cause", "Fault Symptom", "Symptom", "Common Fault", "Fautl Symptom", "Faul Symptom"]
                    causes = next((data[k] for k in cause_keys if k in data), [])

                    if isinstance(causes, str) and causes.strip():
                        st.markdown(f"**Cause:** {causes}")
                    elif isinstance(causes, list):
                        if causes:
                            st.markdown("**Causes:**")
                            for c in causes:
                                st.markdown(f"- {c}")
                        else:
                            st.markdown("**Causes:** ⚠️ None provided.")
                    
                    # === Soluções ===
                    solutions = data.get("solutions", [])

                    if isinstance(solutions, str) and solutions.strip():
                        st.markdown("**Solution:**")
                        st.markdown(f"- {solutions}")
                    elif isinstance(solutions, list):
                        if solutions:
                            st.markdown("**Solutions:**")
                            for s in solutions:
                                st.markdown(f"- {s}")
                        else:
                            st.markdown("**Solutions:** ⚠️ None provided.")
                    # === PPT de Troubleshooting Guide ===
                    pptx_file = data.get("Troubleshooting Guide", "")
                    if pptx_file:
                        pptx_path = os.path.join(BASE_DIR, "resources", pptx_file)
                        if os.path.isfile(pptx_path):
                            safe_name = category.replace(" ", "_").replace(".", "_").lower()
                            with open(pptx_path, "rb") as f:
                                st.download_button(
                                    label="📥 Download Instructions (.pptx)",
                                    data=f,
                                    file_name=pptx_file,
                                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                    key=f"download_{safe_name}_{time.time()}"
                                )
                        else:
                            st.warning("⚠️ Troubleshooting guide file not found.")
                    else:
                        st.warning("⚠️ No troubleshooting guide provided.")

# === Routing ===
if st.session_state.selected_tab == "Log Analyzer":
    run_log_analyzer()
elif st.session_state.selected_tab == "Search Errors":
    run_error_search()
