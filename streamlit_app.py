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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load patterns and database
with open(os.path.join(BASE_DIR, "patterns.json"), "r", encoding="utf-8") as f:
    patterns = json.load(f)

with open(os.path.join(BASE_DIR, "problems_database.json"), "r", encoding="utf-8") as f:
    problems_database = json.load(f)

# UI
st.set_page_config("Endo Service Platform", layout="wide")
st.sidebar.image(os.path.join(BASE_DIR, "images", "mindray_logo_transparent.png"), width=150)
menu = st.sidebar.radio("Navigation", ["Log Analyzer", "Search Errors"])

def extract_tar(file):
    temp_dir = tempfile.mkdtemp()
    tar_path = os.path.join(temp_dir, file.name)
    with open(tar_path, "wb") as f:
        f.write(file.getbuffer())
    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(temp_dir)
    return [os.path.join(root, name) for root, _, files in os.walk(temp_dir) for name in files if name.endswith((".log", ".txt"))]

def analyze_logs(log_files):
    found_issues = defaultdict(list)
    seen = set()
    for file in log_files:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                clean = line.strip()
                if clean and clean not in seen and re.search(r"[a-zA-Z]", clean):
                    for category, pattern in patterns.items():
                        if re.search(pattern, clean, re.IGNORECASE):
                            found_issues[category].append(clean)
                            break
                    else:
                        found_issues["Unclassified"].append(clean)
                    seen.add(clean)
    return found_issues

def render_problem_data(category, lines):
    data = problems_database.get(category)
    with st.expander(f"🔧 {category}", expanded=True):
        for line in lines:
            st.markdown(f"- `{line}`")

        if data:
            st.markdown(f"**Problem:** {data.get('problem', 'N/A')}")
            if data.get("model"):
                st.markdown(f"**Applicable Models:** {', '.join(data['model'])}")
            if data.get("causes"):
                st.markdown("**Causes:**")
                for cause in data["causes"]:
                    st.markdown(f"- {cause}")
            if data.get("solutions"):
                st.markdown("**Solutions:**")
                for sol in data["solutions"]:
                    st.markdown(f"- {sol}")
            if data.get("manual_reference"):
                st.markdown(f"**Manual Reference:** {data['manual_reference']}")
            if data.get("image"):
                img_path = os.path.join(BASE_DIR, "images", data["image"])
                if os.path.exists(img_path):
                    st.image(img_path, width=300)
            if isinstance(data.get("Troubleshooting Guide"), str) and data["Troubleshooting Guide"]:
                ppt_path = os.path.join(BASE_DIR, "resources", data["Troubleshooting Guide"])
                if os.path.exists(ppt_path):
                    with open(ppt_path, "rb") as f:
                        st.download_button("📥 Download Guide", data=f, file_name=data["Troubleshooting Guide"], mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

if menu == "Log Analyzer":
    st.title("📂 Log Analyzer")
    st.info("Upload a `.tar` file generated after decompressing the `.lzo` log.")
    uploaded_file = st.file_uploader("Upload `.tar` file", type=["tar"])
    if uploaded_file:
        with st.spinner("Extracting and analyzing..."):
            try:
                log_files = extract_tar(uploaded_file)
                issues = analyze_logs(log_files)
                if issues:
                    st.success(f"{len(issues)} issue(s) identified.")
                    for key, logs in issues.items():
                        render_problem_data(key, logs)
                else:
                    st.info("✅ No known issue detected.")
            except Exception as e:
                st.error(f"Error: {e}")

if menu == "Search Errors":
    st.title("🔍 Error Search")
    query = st.text_input("Enter a keyword")
    models = sorted(set(chain.from_iterable(v.get("model", []) for v in problems_database.values() if isinstance(v.get("model"), list))))
    selected_model = st.selectbox("Filter by model", ["All"] + models)

    if st.button("Search"):
        results = {}
        for k, v in problems_database.items():
            if query.lower() in k.lower() or query.lower() in json.dumps(v).lower():
                if selected_model == "All" or selected_model in v.get("model", []):
                    results[k] = v

        if results:
            for key, data in results.items():
                render_problem_data(key, [key])
        else:
            st.warning("No results found.")
