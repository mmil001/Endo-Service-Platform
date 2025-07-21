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
PROBLEMS_BY_MODEL_DIR = os.path.join(BASE_DIR, "problems_by_model") # Nova pasta para os arquivos JSON por modelo

# === Carrega usuários ===
def load_users():
    users_path = os.path.join(BASE_DIR, "database", "users.json")
    # Certifique-se de que o diretório 'database' existe
    os.makedirs(os.path.dirname(users_path), exist_ok=True)
    if not os.path.exists(users_path):
        # Cria um arquivo users.json de exemplo se não existir
        with open(users_path, "w", encoding="utf-8") as f:
            json.dump({"admin": {"password": "admin", "expires": "2099-12-31"}}, f)
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

# === Carregar todos os problemas segmentados por modelo ===
def load_problems_by_model():
    all_problems = {}
    if not os.path.exists(PROBLEMS_BY_MODEL_DIR):
        st.warning(f"Diretório '{PROBLEMS_BY_MODEL_DIR}' não encontrado. Certifique-se de que seus arquivos de modelo estão lá.")
        return {}

    for filename in os.listdir(PROBLEMS_BY_MODEL_DIR):
        if filename.endswith(".json"):
            model_name = os.path.splitext(filename)[0]
            filepath = os.path.join(PROBLEMS_BY_MODEL_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    all_problems[model_name] = json.load(f)
            except json.JSONDecodeError:
                st.error(f"Erro ao carregar JSON do arquivo: {filename}")
                continue
    return all_problems

# Carrega os padrões de erro (se ainda forem necessários para outras funcionalidades)
def load_patterns():
    patterns_path = os.path.join(BASE_DIR, "patterns (1).json")
    if os.path.exists(patterns_path):
        with open(patterns_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# === Coletar modelos ===
# Agora, extraímos os nomes dos modelos diretamente dos arquivos carregados
def get_models(problems_data):
    return ['All'] + sorted(list(problems_data.keys()))

# === Tela de login ===
def login_screen():
    st.title("Login de Acesso")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if authenticate(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos, ou sua conta expirou.")

# === Tela principal do aplicativo ===
def main_app():
    st.sidebar.title(f"Bem-vindo, {st.session_state.username}")

    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()

    st.sidebar.header("Navegação")
    tabs = ["Log Analyzer", "Search Errors"]
    st.session_state.selected_tab = st.sidebar.radio("Selecione uma opção", tabs, index=tabs.index(st.session_state.get("selected_tab", "Log Analyzer")))

    # Carrega os problemas e modelos uma vez
    if "all_problems_by_model" not in st.session_state:
        st.session_state.all_problems_by_model = load_problems_by_model()
        st.session_state.available_models = get_models(st.session_state.all_problems_by_model)
    
    # Carrega os padrões (se necessário)
    if "patterns_data" not in st.session_state:
        st.session_state.patterns_data = load_patterns()


# === Log Analyzer ===
def run_log_analyzer():
    st.title("Log Analyzer")
    st.write("Funcionalidade para analisar logs (a ser implementada ou adaptada).")

    # Exemplo de como usar os dados dos modelos aqui, se necessário
    # for model, problems_data in st.session_state.all_problems_by_model.items():
    #     st.write(f"Problemas para {model}: {len(problems_data)}")

# === Search Errors ===
def run_error_search():
    st.title("Search Errors")

    selected_model = st.selectbox(
        "Selecione o Modelo:",
        st.session_state.available_models,
        index=0 # Default to 'All'
    )

    search_query = st.text_input("Enter error code or keywords:")

    if st.button("Search"):
        if not search_query:
            st.warning("Please enter an error code or keywords to search.")
            return

        found_results = {}

        if selected_model == "All":
            # Search across all loaded models
            for model_name, problems_data in st.session_state.all_problems_by_model.items():
                for category, data in problems_data.items():
                    if search_query.lower() in category.lower() or \
                       any(search_query.lower() in str(v).lower() for k, v in data.items() if k not in ["image", "modelo"]):
                        if model_name not in found_results:
                            found_results[model_name] = {}
                        found_results[model_name][category] = data
        else:
            # Search only in the selected model
            problems_data = st.session_state.all_problems_by_model.get(selected_model, {})
            for category, data in problems_data.items():
                if search_query.lower() in category.lower() or \
                   any(search_query.lower() in str(v).lower() for k, v in data.items() if k not in ["image", "modelo"]):
                    if selected_model not in found_results:
                        found_results[selected_model] = {}
                    found_results[selected_model][category] = data

        if found_results:
            st.subheader("Search Results:")
            for model_name, problems_in_model in found_results.items():
                st.markdown(f"### Results for Model: {model_name}")
                for category, data in problems_in_model.items():
                    st.markdown(f"**Error/Problem:** {category}")
                    # Path for images now needs to consider where images are stored relative to BASE_DIR
                    # Assuming images are in BASE_DIR/resources or a similar structure
                    image_path = os.path.join(BASE_DIR, "resources", data.get("image", ""))
                    if image_path and os.path.isfile(image_path):
                        st.image(image_path, caption="Associated image", width=300)

                    st.markdown("**Causes:**")
                    for c in data.get("causes", []):
                        st.markdown(f"- {c}")

                    st.markdown("**Recommended Actions:**")
                    for r in data.get("repairs", []):
                        st.markdown(f"- {r}")

                    # Adiciona download do PPTX se existir
                    safe_name = re.sub(r'[^\\w\\s-]', '', category).strip()
                    pptx_path = os.path.join(BASE_DIR, "resources", f"{safe_name}.pptx")
                    if os.path.isfile(pptx_path):
                        with open(pptx_path, "rb") as f:
                            st.download_button(
                                label="📥 Download Instructions (.pptx)",
                                data=f,
                                file_name=f"{safe_name}.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                key=f"download_{model_name}_{safe_name}" # Unique key
                            )
                    else:
                        st.warning("⚠️ Troubleshooting guide not available.")
                    st.markdown("---") # Separador para facilitar a leitura
        else:
            st.info("No results found.")

# === Routing ===
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login_screen()
else:
    main_app()
    if st.session_state.selected_tab == "Log Analyzer":
        run_log_analyzer()
    elif st.session_state.selected_tab == "Search Errors":
        run_error_search()