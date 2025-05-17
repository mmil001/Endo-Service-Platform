import streamlit as st
import os
import re
import tarfile
import tempfile
import subprocess
import json
from collections import defaultdict
import time
from datetime import datetime
from itertools import chain

# --- Carrega usuários ---
def load_users():
    with open("users.json", "r", encoding="utf-8") as f:
        return json.load(f)

# --- Autenticação ---
def authenticate(username, password):
    users = load_users()
    
    if username not in users:
        return None  # usuário não existe
    
    user = users[username]

    if user.get("password") != password:
        return None  # senha errada
    
    try:
        expiry = datetime.strptime(user["expires"], "%Y-%m-%d")
        if expiry < datetime.today():
            return None  # licença expirada
    except:
        return None  # data inválida
    
    return user.get("role")  # ✅ corrigido aqui

# --- Tela de login ---
def login_screen():
    st.image("mindray_logo_transparent.png", width=150)
    st.markdown("## 🔐 Endo Service Platform - Login")
    st.markdown("Please enter your credentials to access the platform.")
    st.markdown("---")

    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    if st.button("Login"):
        role = authenticate(username, password)
        if role:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = role
            st.rerun()
        else:
            st.error("Access denied. Invalid user, password, or expired license.")

# --- Controle de login ---
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login_screen()
    st.stop()

# Config inicial
st.set_page_config(page_title="Endo Service Platform", layout="wide")
st.image("mindray_logo_transparent.png", width=150)

# --- Banco de erros ---
if "problems_database" not in st.session_state:
    with open("problems_database.json", "r", encoding="utf-8") as f:
        st.session_state.problems_database = json.load(f)
problems_database = st.session_state.problems_database

patterns = {
    "Contamination Detected 🧫": r"(contamin|liquid.*detected|inlet.*liquid|pollution.*mark|level sensor error|ERR#08)",
    "Communication Errors 🔵": r"(connect.*failed|network.*unreach|ipc.*fail|timeout|socket.*error)",
    "Heating Errors 🔥": r"(heat.*fail|temperature.*alarm|ERR#14|ERR#15|heating plate|tube.*fail)",
    "Insufflator Errors 🧪": r"(flow.*error|pressure.*fail|valve.*fail|ERR#04|gas leak|pinch.*valve)",
    "Insufflation / Flow Errors 🧪": r"(proportional valve|zero drift|ERR#0[4-9]|ERR#1[0-2])",
    "Power Supply Errors ⚡": r"(power.*fail|fuse.*blown|voltage.*error|ERR#06|no power)",
    "Image Processor / Camera Errors 🎥": r"(video.*lost|camera.*error|CCU.*fail|no signal|image.*not found|firmware.*error|hdmi|dvi|sdi.*fail)",
    "Camera Head Errors 🎯": r"(camera head.*error|optical.*fail|coupler|lens|focus.*fail|zoom.*fail|no.*camera.*input)",
    "Video Recording / USB Errors 📀": r"(usb.*fail|record.*error|video.*not saved|no.*recording|file.*system.*error)"
}

# --- Tabs por tipo de usuário ---
if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = "Log Analyzer"

menu = ["Log Analyzer", "Search Errors"]
if st.session_state.get("role") == "master":
    menu.append("Admin Panel")

st.session_state.selected_tab = st.sidebar.radio(
    "Navigation",
    menu,
    index=menu.index(st.session_state.selected_tab)
)

# Botão de logout no menu lateral
with st.sidebar:
    if st.button("🔲 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state["logged_in"] = False
        st.rerun()

# --- Interface por aba ---
def show_user_panel():
    if st.session_state.selected_tab == "Log Analyzer":
        st.title("🛠️ Endo-Service Platform")
        run_log_analyzer()
    elif st.session_state.selected_tab == "Search Errors":
        st.title("📚 Error Libraries")
        run_error_search()

# Função Log Analyzer
def run_log_analyzer():
    # Instruções para preparar o arquivo
    st.markdown("### 📌 IMPORTANT — How to Prepare the Log File")
    st.info("""
The log file exported from the equipment is in `.lzo` format, which cannot be analyzed directly on this platform.

Please follow these steps:

1. Copy the `.lzo` file from the equipment to your computer or USB drive.
2. Double-click the file `Converter_LZO.bat` provided by Mindray.
3. The script will automatically generate a `.tar` file (e.g., `log.tar`) in the same folder.
4. Upload the generated `.tar` file below for analysis.

> If you do not have the converter tool, please contact Mindray Technical Support.
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
        output = []
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
            time.sleep(0.1)
        compiled = {cat: re.compile(pat, re.IGNORECASE) for cat, pat in patterns.items()}
        issues = defaultdict(list)
        for i, line in enumerate(all_lines):
            for category, regex in compiled.items():
                if regex.search(line):
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{2})", line)
                    date_str = date_match.group(1) if date_match else "0000-00-00"
                    issues[category].append(date_str)
            if i % 10 == 0:
                progress = 50 + int((i / len(all_lines)) * 50)
                progress_bar.progress(progress, text=f"Analyzing logs... ({progress}%)")
        progress_bar.progress(100, text="✅ Analysis complete.")
        return issues

    if uploaded_file:
        with st.spinner("Extracting file..."):
            try:
                log_files = extract_tar(uploaded_file)
                st.success(f"Extracted {len(log_files)} log files.")
                issues = analyze_logs(log_files)
                if issues:
                    st.subheader("⚠️ Diagnosed Issues")
                    for category, dates in sorted(issues.items(), key=lambda x: max(x[1], default=""), reverse=True):
                        data = problems_database.get(category)
                        with st.expander(f"🔧 {category} — {len(dates)} occurrences"):
                            if data:
                                st.markdown(f"**Problem:** {data['problem']}")
                                image_file = data.get("image")
                                image_path = os.path.join("images", image_file) if image_file else None
                                if image_path and os.path.isfile(image_path):
                                    st.image(image_path, caption="Associated image", width=300)
                                else:
                                    st.info("Image not found.")

                                # Mapeia o nome da categoria para o nome do arquivo .pptx
                                category_to_file = {
                                    "Contamination Detected 🧫": "Contamination Detected.pptx"
                                # Adicione outros se quiser
                                }

                                file_name = category_to_file.get(category)

                                if file_name:
                                    pptx_path = os.path.join("resources", file_name)
                                    if os.path.isfile(pptx_path):
                                        with open(pptx_path, "rb") as f:
                                            st.download_button(
                                                label="📥 Download Instructions (.pptx)",
                                                data=f,
                                                file_name=file_name,
                                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                                            )
                                    else:
                                        st.warning("⚠️ File not found in 'resources'.")
                                else:
                                    st.info("ℹ️ No instructions available for this error.")

                                def remove_emojis(text):
                                    return re.sub(r'[^\w\s\-]', '', text).strip()

                                safe_name = remove_emojis(category)
                                pptx_path = os.path.join("resources", f"{safe_name}.pptx")
                                st.markdown("---")  # só pra separar visualmente
                                st.write("🔍 Caminho do arquivo:", pptx_path)
                                st.write("📂 Existe?", os.path.isfile(pptx_path))
                                if os.path.isfile(pptx_path):
                                    with open(pptx_path, "rb") as f:
                                        st.download_button(
                                            label="📥 Download Instructions (.pptx)",
                                            data=f,
                                            file_name=f"{safe_name}.pptx",
                                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                                        )
       
                            else:
                                st.markdown("No detailed data found for this error.")
                else:
                    st.info("No problems detected.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# Search Errors
from itertools import chain

def run_error_search():
    st.subheader("🔍 Search Errors")

    query = st.text_input("Enter a keyword (e.g., 'contamination')")

    # Coleta de todos os modelos válidos
    model_set = set(chain.from_iterable(
        v.get("modelo", []) for v in problems_database.values() if isinstance(v.get("modelo"), list)
    ))
    models = ['All'] + sorted(model_set)

    # Filtro com blocos (radio)
    selected_model = st.radio("📌 Filter by Equipment Model", models, horizontal=True)

    col_left, col_spacer, col_right = st.columns([1, 8, 1])
    with col_left:
        search_clicked = st.button("Search")
    with col_right:
        clear_clicked = st.button("Clear")

    if clear_clicked:
        st.session_state.pop("query", None)
        st.session_state.selected_tab = "Search Errors"
        st.rerun()

    results = {}

    if search_clicked:
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
                results[key] = value

    if results:
        for category, data in results.items():
            with st.expander(f"🔧 {category}"):
                st.markdown(f"**Problem:** {data['problem']}")

                if "modelo" in data:
                    st.markdown(f"**Applicable Models:** {', '.join(data['modelo'])}")

                image_file = data.get("image")
                image_path = os.path.join("images", image_file) if image_file else None
                if image_path and os.path.isfile(image_path):
                    st.image(image_path, caption="Associated image", width=300)
                else:
                    st.info("Image not found.")

                st.markdown("**Causes:**")
                for c in data['causes']:
                    st.markdown(f"- {c}")

                st.markdown("**Recommended Actions:**")
                for r in data['repairs']:
                    st.markdown(f"- {r}")

                if category == "Contamination Detected 🧫":
                    pptx_path = "resources/Contamination Detected.pptx"
                    if os.path.isfile(pptx_path):
                        with open(pptx_path, "rb") as f:
                            st.download_button(
                                label="📥 Download Instructions (.pptx)",
                                data=f,
                                file_name="Contamination Detected.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                            )
                    else:
                        st.warning("⚠️ Arquivo não encontrado.")

    elif search_clicked:
        st.info("No results found.")              

# Admin Panel
def run_admin_panel():
    st.subheader("🛠️ Admin Panel")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ Add New Entry"):
            st.session_state["admin_mode"] = "add"
            for k in ["keyword_input", "problem_input", "causes_input", "solutions_input", "models_input"]:
                st.session_state.pop(k, None)
            st.rerun()

    with col2:
        if st.button("✏️ Edit Existing Entry"):
            st.session_state["admin_mode"] = "edit"

    with col3:
        if st.button("🧹 Clear / Log Out"):
            st.session_state.auth = False
            st.session_state.show_password_input = False
            st.session_state.selected_tab = "Log Analyzer"
            for k in ["keyword_input", "problem_input", "causes_input", "solutions_input", "models_input", "admin_mode"]:
                st.session_state.pop(k, None)
            st.rerun()

    if st.session_state.get("admin_mode") == "edit":
        st.markdown("### 🔍 Select Existing Error to Edit")
        selected_error = st.selectbox("Choose a category to edit", [""] + list(problems_database.keys()))
        if selected_error:
            existing = problems_database[selected_error]
            st.session_state["keyword_input"] = selected_error
            st.session_state["problem_input"] = existing["problem"]
            st.session_state["causes_input"] = "\n".join(existing["causes"])
            st.session_state["solutions_input"] = "\n".join(existing["repairs"])
            st.session_state["models_input"] = existing.get("modelo", [])

    if st.session_state.get("admin_mode") in ["add", "edit"]:
        st.markdown("### 📝 Error Information")
        keyword = st.text_input("Keyword / Category", key="keyword_input")
        problem = st.text_input("Problem Description", key="problem_input")
        causes = st.text_area("Causes (one per line)", key="causes_input").splitlines()
        solutions = st.text_area("Solutions (one per line)", key="solutions_input").splitlines()

        all_models = ["HD3", "U1", "R1", "UX1", "UX3", "UX5", "UX7", "HB100", "HB200L", "HB300", "HB300R", "HB500", "HB500R", "HS-50F"]
        selected_models = st.multiselect("Applicable Equipment Models", all_models, default=st.session_state.get("models_input", []))

        image = st.file_uploader("Upload an image (optional)", type=["jpg", "png"])

        col_save, col_delete = st.columns([4, 1])
        with col_save:
            save = st.button("💾 Save to Database")
        with col_delete:
            delete = st.button("🗑️ Delete Error")

        if delete and st.session_state.get("admin_mode") == "edit" and keyword in problems_database:
            image_file = problems_database[keyword].get("image", "")
            image_path = os.path.join("images", image_file)
            if image_file and os.path.isfile(image_path):
                os.remove(image_path)
            del problems_database[keyword]
            with open("problems_database.json", "w", encoding="utf-8") as f:
                json.dump(problems_database, f, indent=4, ensure_ascii=False)
            st.session_state.problems_database = problems_database
            st.success("Entry deleted successfully.")
            st.rerun()

        if save:
            if keyword and problem:
                os.makedirs("images", exist_ok=True)
                image_filename = None
                if image is not None:
                    ext = os.path.splitext(image.name)[1].lower()
                    image_filename = f"{keyword}{ext}"
                    image_path = os.path.join("images", image_filename)
                    with open(image_path, "wb") as f:
                        f.write(image.getbuffer())

                problems_database[keyword] = {
                    "problem": problem,
                    "causes": causes,
                    "repairs": solutions,
                    "image": image_filename if image_filename else "",
                    "modelo": selected_models
                }

                with open("problems_database.json", "w", encoding="utf-8") as f:
                    json.dump(problems_database, f, indent=4, ensure_ascii=False)

                st.session_state.problems_database = problems_database
                st.success(f"Entry for '{keyword}' saved successfully.")
                for k in ["keyword_input", "problem_input", "causes_input", "solutions_input", "models_input", "admin_mode"]:
                    st.session_state.pop(k, None)
                st.rerun()
            else:
                st.warning("Keyword and Problem Description are required.")

                # Atualiza o JSON
                with open("problems_database.json", "w", encoding="utf-8") as f:
                    json.dump(problems_database, f, indent=4, ensure_ascii=False)

                # Atualiza a variável de sessão
                st.session_state.problems_database = problems_database

                st.success(f"Entry for '{keyword}' saved successfully.")
                for k in ["keyword_input", "problem_input", "causes_input", "solutions_input", "admin_mode"]:
                    st.session_state.pop(k, None)
                st.session_state.auth = False
                st.session_state.selected_tab = "Log Analyzer"
                st.rerun() 

        if st.session_state.get("awaiting_next_entry"):
            next_action = st.radio("Do you want to add or edit another entry?", ["Yes", "No"], key="add_more_radio")
    
            if next_action == "Yes":
                # Marcar que é nova entrada, limpar modo e reiniciar
                for k in ["keyword_input", "problem_input", "causes_input", "solutions_input", "admin_mode"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state.awaiting_next_entry = False
                st.rerun()
    
            elif next_action == "No":
                st.session_state.selected_tab = "Log Analyzer"
                st.session_state.awaiting_next_entry = False
                for k in ["keyword_input", "problem_input", "causes_input", "solutions_input", "admin_mode"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

# Routing
if st.session_state.selected_tab == "Log Analyzer":
    show_user_panel()

elif st.session_state.selected_tab == "Search Errors":
    show_user_panel()

elif st.session_state.selected_tab == "Admin Panel":
    if st.session_state["role"] == "master":
        run_admin_panel()
    else:
        st.error("Access denied. Only administrators can access the Admin Panel.")

#Rodar isso no terminal para salvar as alterações:
#git add .
#git commit -m "Update login screen design and add logout button"
#git push origin main

