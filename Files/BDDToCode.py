import os
import time
import json
import re
from dotenv import load_dotenv
import sqlite3
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

# =========================
# ENV + DB CONFIG
# =========================
load_dotenv()
database_name = os.getenv("LOCAL_DB_NAME")

if not database_name:
    st.error("Database Name not found. Please check your .env file.")
    st.stop()

DB_FILE = database_name + ".db"


# =========================
# DB INIT & HELPERS
# =========================
def init_db():
    """Initialize database tables for projects and BDD files."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ProjectDetails (
            project_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name    TEXT UNIQUE,
            project_lang    TEXT,
            project_fw      TEXT,
            project_path    TEXT,
            created_date    TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS BDDDetails (
            file_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name    TEXT,
            file_content TEXT,
            created_date TEXT,
            project_id   INTEGER
        )
    """)
    conn.commit()
    conn.close()


def get_db():
    """Get database connection with row factory enabled."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# FILE EXTRACTION (unchanged)
# =========================
def extract_files_from_generated_code(content):
    files = {}
    match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        try:
            json_content = match.group(1)
            files = json.loads(json_content)
            return files
        except:
            pass
    pattern = r"(?:#\s*File:\s*|###\s*|--\s*filename:\s*)([^\n]+)\n"
    matches = list(re.finditer(pattern, content))
    if not matches:
        return {"generated_code.py": content}
    for i in range(len(matches)):
        filename = matches[i].group(1).strip()
        start = matches[i].end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
            file_content = content[start:end].strip()
        else:
            file_content = content[start:].strip()
        files[filename] = file_content
    return files if files else {"generated_code.py": content}


def safe_parse_result(result):
    if isinstance(result, dict):
        return result
    elif isinstance(result, str):
        try:
            return json.loads(result)
        except:
            return {"generated_code.py": result}
    return result


def get_files_from_result(result):
    files = {}
    parsed = safe_parse_result(result)
    if isinstance(parsed, dict):
        for fname, fdata in parsed.items():
            if isinstance(fdata, str):
                files[fname] = fdata
            elif isinstance(fdata, dict):
                files[fname] = fdata.get("content") or fdata.get("code") or fdata.get("file_content")
    if "generated_code.py" in files and len(files) == 1:
        extracted = extract_files_from_generated_code(files["generated_code.py"])
        if extracted:
            files = extracted
    if not files:
        files = {"generated_code.py": str(result)}
    return files


# =========================
# SAVE FILES - FIXED CACHE CLEARING
# =========================
def save_files_to_folder(files_dict, base_folder):
    saved_files = []
    failed_files = []
    try:
        os.makedirs(base_folder, exist_ok=True)
        for filename, content in files_dict.items():
            try:
                full_path = os.path.join(base_folder, filename)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                saved_files.append(full_path)
            except Exception as e:
                failed_files.append(f"{filename}: {str(e)}")
        return saved_files, failed_files
    except Exception as e:
        return [], [f"Base folder error: {str(e)}"]


# =========================
# TASK POLLING (unchanged)
# =========================
def check_task_status(task_id):
    try:
        response = requests.get(f"http://127.0.0.1:8000/task-result/{task_id}", timeout=10)
        return response.json()
    except:
        return None


def poll_task(task_id):
    for _ in range(60):
        result = check_task_status(task_id)
        if result:
            if result.get("status") == "done":
                return result.get("result")
            elif result.get("status") == "error":
                st.error(result.get("result"))
                return None
        time.sleep(2)
    st.warning("Task timed out.")
    return None


# =========================
# PROJECT OPERATIONS - NO CACHING
# =========================
def get_projects():  # 🔥 NO CACHE - always fresh
    db = get_db()
    return [dict(r) for r in db.execute("SELECT * FROM ProjectDetails").fetchall()]


def get_unique_latest_bdd_files(project_id):  # 🔥 NO CACHE - always fresh
    """Get UNIQUE BDD filenames with only LATEST version for each filename."""
    db = get_db()
    latest_files = db.execute("""
        SELECT DISTINCT b1.*
        FROM BDDDetails b1
        INNER JOIN (
            SELECT file_name, MAX(file_id) as max_id
            FROM BDDDetails 
            WHERE project_id = ?
            GROUP BY file_name
        ) b2 ON b1.file_name = b2.file_name AND b1.file_id = b2.max_id
        WHERE b1.project_id = ?
        ORDER BY b1.created_date DESC
    """, (project_id, project_id)).fetchall()
    return [dict(r) for r in latest_files]


def create_project_structure(project_dir, lang, fw):
    os.makedirs(project_dir, exist_ok=True)
    base_folders = ["tests", "pages"]
    if lang == "Python":
        if fw == "Pytest":
            base_folders += ["utils", "fixtures"]
        elif fw == "Behave":
            base_folders += ["features", "steps", "environment"]
    for folder in base_folders:
        os.makedirs(os.path.join(project_dir, folder), exist_ok=True)


def handle_create_project():
    with st.form("create_project_form"):
        col1, col2 = st.columns([2, 1])
        with col1:
            p_name = st.text_input("Project Name", help="Unique name for your project")
        with col2:
            lang = st.selectbox("Language", ["Python", "Java", "C#"])
            fw_options = ["Pytest", "Behave"] if lang == "Python" else ["Cucumber", "TestNG"]
            fw = st.selectbox("Framework", fw_options)
        p_path = st.text_input("Base Path", value="C:/QA_Automation", help="Root directory for projects")
        submitted = st.form_submit_button("🚀 Create Project")
        if submitted and p_name.strip():
            project_dir = os.path.join(p_path, p_name)
            create_project_structure(project_dir, lang, fw)
            db = get_db()
            db.execute(
                "INSERT INTO ProjectDetails (project_name, project_lang, project_fw, project_path, created_date) VALUES (?, ?, ?, ?, ?)",
                (p_name, lang, fw, project_dir, datetime.now().strftime("%Y-%m-%d"))
            )
            db.commit()
            st.success(f"✅ Project '{p_name}' created successfully!")
            st.balloons()
            st.rerun()
        elif submitted:
            st.error("Please enter a valid project name.")


def handle_select_project():
    """Handle existing project selection with ALL fixes."""
    projects = get_projects()
    if not projects:
        st.warning("No projects found. Create a new project first.")
        return

    project_names = [p["project_name"] for p in projects]
    sel_proj = st.selectbox("👑 **Choose Project**", project_names)
    proj = next(p for p in projects if p["project_name"] == sel_proj)

    # 🔥 STEP 1: Choose Source (BIG AND CLEAR)
    st.markdown("## 🎯 **STEP 1: Choose BDD Source**")
    source_choice = st.selectbox(
        "**Where should the BDD file come from?**",
        ["📄 Database (Latest unique files)", "📤 Upload new file"],
        index=0,
        key="source_choice_main"
    )

    # 🔥 Variables to track if user completed selection
    has_valid_selection = False
    bdd_content = None
    bdd_filename = None

    # 🔥 STEP 2A: DATABASE OPTION
    if source_choice == "📄 Database (Latest unique files)":
        st.markdown("---")
        st.markdown("### 📊 **Database Files Available**")

        unique_latest_bdd_files = get_unique_latest_bdd_files(proj["project_id"])  # 🔥 Always fresh

        if unique_latest_bdd_files:
            bdd_options = [f"📄 {f['file_name']} (ID: {f['file_id']}) - {f['created_date']}" for f in
                           unique_latest_bdd_files]
            selected_bdd = st.selectbox("**Select BDD file:**", bdd_options, key="db_select")

            if selected_bdd:
                selected_file = next(
                    f for f in unique_latest_bdd_files if
                    f"📄 {f['file_name']} (ID: {f['file_id']}) - {f['created_date']}" == selected_bdd)

                st.markdown("### 📋 **File Preview**")

                edited_bdd_content = st.text_area(
                    "BDD File Content (editable):",
                    value=selected_file["file_content"],
                    height=300,
                    key=f"edit_db_{selected_file['file_id']}"
                )

                bdd_content = edited_bdd_content
                bdd_filename = selected_file["file_name"]
                has_valid_selection = True

                original_length = len(selected_file["file_content"])
                edited_length = len(edited_bdd_content)
                if edited_bdd_content != selected_file["file_content"]:
                    st.success("✏️ **Content modified** - " + str(edited_length - original_length) + " chars changed")

                st.markdown("✅ **Database file ready!**")
        else:
            st.warning("❌ **No BDD files found** for this project in database")

    # 🔥 STEP 2B: UPLOAD OPTION - EDITABLE
    elif source_choice == "📤 Upload new file":
        st.markdown("---")
        st.markdown("### 📤 **Upload Section**")

        uploaded_file = st.file_uploader(
            "**Choose .feature or .txt file:**",
            type=["feature", "txt"],
            key="upload_main"
        )

        if uploaded_file is not None:
            # 🔥 Read uploaded content once
            if "uploaded_content" not in st.session_state:
                st.session_state.uploaded_content = uploaded_file.read().decode("utf-8")
                st.session_state.uploaded_filename = uploaded_file.name

            # 🔥 Checkbox to make editable
            make_editable = st.checkbox("✏️ Make uploaded file editable", key="make_upload_editable")

            bdd_content = st.session_state.uploaded_content
            bdd_filename = st.session_state.uploaded_filename
            has_valid_selection = True

            st.markdown("### 📋 **Uploaded File Preview**")
            if make_editable:
                edited_upload_content = st.text_area(
                    "Edit uploaded content:",
                    value=bdd_content,
                    height=300,
                    key="edit_upload_content"
                )
                bdd_content = edited_upload_content
                if edited_upload_content != st.session_state.uploaded_content:
                    st.success("✏️ **Uploaded file modified!**")
            else:
                st.code(bdd_content, language="gherkin")

            st.markdown("✅ **Upload ready!**")

    # 🔥 STEP 3: GENERATE BUTTON
    if has_valid_selection and bdd_content is not None:
        st.markdown("---")
        st.markdown("## 🚀 **STEP 2: Generate Code**")
        st.markdown(f"**Using**: `{bdd_filename}`")

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🤖 **GENERATE CODE NOW**", type="primary", use_container_width=True):
                # 🔥 SAVE EDITED BDD TO DATABASE FIRST
                db = get_db()
                db.execute(
                    """
                    INSERT INTO BDDDetails (file_name, file_content, created_date, project_id)
                    VALUES (?,?,?,?)
                    """,
                    (
                        bdd_filename,
                        bdd_content,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        proj["project_id"],
                    ),
                )
                db.commit()
                st.success(f"✅ **BDD file '{bdd_filename}' saved to database!**")

                # 🔥 GENERATE CODE
                with st.spinner("Generating code... This may take a few minutes."):
                    payload = {
                        "project_name": proj["project_name"],
                        "language": proj["project_lang"],
                        "framework": proj["project_fw"],
                        "project_path": proj.get("project_path", ""),
                        "bdd_content": bdd_content
                    }
                    try:
                        res = requests.post("http://127.0.0.1:8000/generate-agent-code", json=payload, timeout=300)
                        task_id = res.json()["task_id"]
                        result = poll_task(task_id)
                        if result:
                            st.session_state.generated_result = result
                            st.session_state.show_save_section = True
                            st.session_state.selected_project = proj
                            st.success("✅ **Code generated successfully!**")
                    except Exception as e:
                        st.error(f"❌ **Backend error**: {str(e)}")

        with col2:
            st.info("**Project Info**")
            st.write(f"• **{proj['project_name']}**")
            st.write(f"• **{proj['project_lang']}**")
            st.write(f"• **{proj['project_fw']}**")
    else:
        st.markdown("---")
        st.markdown("### ⏳ **Waiting for file selection...**")
        st.info("👆 **Choose a source above and select/upload a file to enable Generate button**")


def show_save_ui():
    if "generated_result" not in st.session_state or not st.session_state.generated_result:
        return

    proj = st.session_state.selected_project
    files = get_files_from_result(st.session_state.generated_result)

    st.markdown("### 💾 **Save Generated Files**")
    default_path = proj.get("project_path", os.getcwd())
    folder_path = st.text_input("📁 Save to Folder:", value=default_path,
                                help="Where to save the generated files")

    st.markdown("**Files to generate:**")
    for fname in files.keys():
        st.write(f"• {fname}")

    if st.button("💾 **SAVE ALL FILES**", type="primary", use_container_width=True):
        if not folder_path.strip():
            st.error("Please enter a valid folder path.")
            return
        saved, failed = save_files_to_folder(files, folder_path)
        if saved:
            st.success(f"✅ {len(saved)} files saved successfully!")
            st.balloons()
            # 🔥 CRITICAL FIX: Clear session state AND force cache refresh
            for key in ["generated_result", "show_save_section", "selected_project"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.cache_data.clear()  # 🔥 FORCE CACHE CLEAR
            time.sleep(3)
            st.rerun()  # 🔥 IMMEDIATE RERUN with fresh data
        if failed:
            for error in failed:
                st.error(f"❌ {error}")


# =========================
# MAIN APP
# =========================
def run_app():
    init_db()
    st.set_page_config(page_title="AI QA Agent", layout="wide")
    st.title("🤖 **AI QA Agent**")

    # 🔹 Show backend health immediately on app start
    st.markdown("### **Backend Health Status**")
    if st.button("Check Backend Health"):
        try:
            res = requests.get("http://127.0.0.1:8000/health", timeout=5)
            if res.status_code == 200:
                st.markdown(f"""
                    <div style="
                        border: 2px solid #4CAF50;
                        background-color: #e6ffe6;
                        padding: 15px;
                        border-radius: 10px;
                        color: #006400;
                        font-weight: bold;
                    ">
                    ✅ Backend is running (Status {res.status_code})
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style="
                        border: 2px solid #ff4c4c;
                        background-color: #ffe6e6;
                        padding: 15px;
                        border-radius: 10px;
                        color: #a70000;
                        font-weight: bold;
                    ">
                    ❌ Backend unhealthy (Status {res.status_code})
                    </div>
                    """, unsafe_allow_html=True)
        except requests.exceptions.RequestException as e:
            st.markdown(f"""
                <div style="
                    border: 2px solid #ff4c4c;
                    background-color: #ffe6e6;
                    padding: 15px;
                    border-radius: 10px;
                    color: #a70000;
                    font-weight: bold;
                ">
                ❌ Backend unavailable: {e}
                </div>
                """, unsafe_allow_html=True)

    # 🔥 Initialize session state
    for key in ["generated_result", "show_save_section", "selected_project"]:
        if key not in st.session_state:
            st.session_state[key] = None

    st.markdown("---")
    mode = st.radio("🎯 **Choose Action**:", ["Create New Project", "Select Existing Project"])

    if mode == "Create New Project":
        st.markdown("### ➕ **Create New Project**")
        handle_create_project()
    elif mode == "Select Existing Project":
        st.markdown("### 📂 **Select Existing Project**")
        handle_select_project()

        if (st.session_state.show_save_section and
                st.session_state.generated_result and
                st.session_state.selected_project):
            st.markdown("---")
            with st.expander("🔍 **Generated Response**", expanded=True):
                st.code(str(st.session_state.generated_result), language="json")
            show_save_ui()

    with st.expander("📊 **Database View**", expanded=False):
        db = get_db()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Projects")
            st.dataframe(pd.read_sql_query("SELECT * FROM ProjectDetails", db))
        with col2:
            st.subheader("BDD Files")
            st.dataframe(pd.read_sql_query("SELECT * FROM BDDDetails ORDER BY created_date DESC", db))


if __name__ == "__main__":
    run_app()
