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

load_dotenv()
database_name = os.getenv("LOCAL_DB_NAME")

if not database_name:
    st.error("Database Name not found. Please check your .env file.")
    st.stop()
DB_FILE = database_name + ".db"

base_url = None
login_username = None
login_password = None


def init_db():
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
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


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


def get_projects():
    db = get_db()
    return [dict(r) for r in db.execute("SELECT * FROM ProjectDetails").fetchall()]


def get_unique_latest_bdd_files(project_id):
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


def create_project_structure(project_dir, lang, fw, base_url, login_username, login_password):
    os.makedirs(project_dir, exist_ok=True)
    base_folders = ["tests"]
    if lang == "Python":
        if fw == "Pytest":
            base_folders += ["features", "fixtures", "steps"]
        elif fw == "Behave":
            base_folders += ["features", "steps", "environment"]
    for folder in base_folders:
        folder_path = os.path.join(project_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        if fw in ("Pytest", "Behave"):
            init_file = os.path.join(folder_path, "__init__.py")
            if not os.path.exists(init_file):
                open(init_file, "w").close()

    if fw in ("Pytest", "Behave"):
        root_init = os.path.join(project_dir, "__init__.py")
        if not os.path.exists(root_init):
            open(root_init, "w").close()

    # Create .env file at root directory
    env_file = os.path.join(project_dir, ".env")
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            f.write(f"BASE_URL={base_url}\n")
            f.write(f"LOGIN_USERNAME={login_username}\n")
            f.write(f"LOGIN_PASSWORD={login_password}\n")


def handle_create_project():
    with st.form("create_project_form"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            p_name = st.text_input("Project Name", help="Unique name for your project")
        with col2:
            lang = st.selectbox("Language", ["Python", "Java", "C#"])
        with col3:
            fw_options = ["Pytest", "Behave"] if lang == "Python" else ["Cucumber", "TestNG"]
            fw = st.selectbox("Framework", fw_options)

        base_url = st.text_input("Enter Base URL")
        col1, col2 = st.columns([1, 1])
        with col1:
            login_username = st.text_input("Enter Username")
        with col2:
            login_password = st.text_input("Enter Password")

        base_path = os.path.dirname(os.path.abspath(__file__))
        p_path = st.text_input("Base Path", value=base_path, help="Root directory for projects")

        submitted = st.form_submit_button("Create Project Structure")
        if submitted and p_name.strip():
            project_dir = os.path.join(p_path, p_name)
            create_project_structure(project_dir, lang, fw, base_url, login_username, login_password)
            db = get_db()
            db.execute(
                "INSERT INTO ProjectDetails (project_name, project_lang, project_fw, project_path, created_date) VALUES (?, ?, ?, ?, ?)",
                (p_name, lang, fw, project_dir, datetime.now().strftime("%Y-%m-%d"))
            )
            db.commit()
            st.success(f"✅ Project '{p_name}' created successfully!")
            time.sleep(2)
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
    sel_proj = st.selectbox("**Choose Project**", project_names)
    proj = next(p for p in projects if p["project_name"] == sel_proj)

    st.markdown("## **STEP 1: Choose BDD Source**")
    source_choice = st.selectbox(
        "**Where should the BDD file come from?**",
        ["📄 Load recent BDD file from Database", "📤 Upload new file"],
        index=0,
        key="source_choice_main"
    )

    has_valid_selection = False
    bdd_content = None
    bdd_filename = None

    if source_choice == "📄 Load recent BDD file from Database":
        st.markdown("---")
        st.markdown("### ✅ **Database file found**")

        unique_latest_bdd_files = get_unique_latest_bdd_files(proj["project_id"])

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
        else:
            st.warning("❌ **No BDD files found** for this project in database")

    elif source_choice == "📤 Upload new file":
        st.markdown("---")
        st.markdown("### 📤 **Upload Section**")

        uploaded_file = st.file_uploader(
            "**Choose .feature or .txt file:**",
            type=["feature", "txt"],
            key="upload_main"
        )

        if uploaded_file is not None:
            if "uploaded_content" not in st.session_state:
                st.session_state.uploaded_content = uploaded_file.read().decode("utf-8")
                st.session_state.uploaded_filename = uploaded_file.name

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

    if has_valid_selection and bdd_content is not None:
        st.markdown("---")
        st.markdown("## **STEP 2: Generate Code**")
        st.markdown(f"**Using**: `{bdd_filename}`")
        project_path = proj.get("project_path", "")

        env_file = os.path.join(project_path, ".env")
        base_url = ""
        login_username = ""
        login_password = ""
        selected_elements = ""
        locator_content = ""
        combined_data = {}

        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("BASE_URL="):
                        base_url = line.split("=", 1)[1]
                    elif line.startswith("LOGIN_USERNAME="):
                        login_username = line.split("=", 1)[1]
                    elif line.startswith("LOGIN_PASSWORD="):
                        login_password = line.split("=", 1)[1]
            # st.success(f".env file loaded successfully!")
        else:
            st.warning(f".env file not found at: {env_file}")

        st.markdown(f"**Add Supporting Information**")

        # Initialize session state
        if "support_content" not in st.session_state:
            st.session_state.support_content = ""

        # Checkboxes for each field
        include_base_url = st.checkbox(f"Base URL: {base_url}")
        include_username = st.checkbox(f"Username: {login_username}")
        include_password = st.checkbox(f"Password: {'*' * len(login_password)}")

        support_content = ""
        selected_fields = []
        if include_base_url:
            selected_fields.append(f"Base URL: {base_url}")
        if include_username:
            selected_fields.append(f"Username: {login_username}")
        if include_password:
            selected_fields.append(f"Password: {login_password}")

        for i, field in enumerate(selected_fields):
            if i < len(selected_fields) - 1:
                support_content += f"{field},\n"
            else:
                support_content += f"{field}\n"

        st.session_state.support_content = support_content

        st.markdown("---")
        st.markdown(f"**Upload Element Locator File**")

        # File uploader for Excel
        uploaded_file = st.file_uploader("Browse Element Locator Excel File", type=["xlsx", "xls"])

        if uploaded_file is not None:
            import pandas as pd

            # Read all sheets
            all_sheets = pd.read_excel(uploaded_file, sheet_name=None, header=0)

            # Combine column 2 (element name), column 3 (element locator), column 4 (type) from all sheets
            for sheet_name, df in all_sheets.items():
                if df.shape[1] >= 3:  # Ensure at least 3 columns exist
                    for _, row in df.iterrows():
                        element_name = row.iloc[1]  # Column 2 (index 1)
                        element_locator = row.iloc[2]  # Column 3 (index 2)
                        element_type = row.iloc[3] if df.shape[1] >= 4 else ""  # Column 4 (index 3)
                        if pd.notna(element_name) and pd.notna(element_locator):
                            combined_data[str(element_name)] = {
                                "locator": str(element_locator),
                                "type": str(element_type) if pd.notna(element_type) else ""
                            }

            if combined_data:
                # Multiselect dropdown with element names
                selected_elements = st.multiselect(
                    "Select Element Names",
                    options=list(combined_data.keys())
                )

                # Display locators and types for selected elements
                if selected_elements:
                    st.markdown("**Selected Element Locators:**")

                    for i, element in enumerate(selected_elements):
                        locator = combined_data[element]["locator"]
                        element_type = combined_data[element]["type"]
                        type_display = f" *(Type: {element_type})*" if element_type else ""
                        st.write(f"**{element}**{type_display}: `{locator}`")

                        # Build locator_content with type
                        entry = f"{element} (Type: {element_type}): {locator}" if element_type else f"{element}: {locator}"
                        if i < len(selected_elements) - 1:
                            locator_content += f"{entry},\n"
                        else:
                            locator_content += f"{entry}\n"

                    # Append locators to support_content in session state
                    st.session_state.support_content = support_content + "\nElement Locators:\n" + locator_content
            else:
                st.warning("No valid data found in the uploaded file. Ensure columns 2, 3 and 4 have data.")

        st.session_state.support_content = support_content + (
            "\nElement Locators:\n" + locator_content if locator_content else ""
        )

        st.markdown("---")
        st.markdown(f"**Support Content collected**")
        masked_content = st.session_state.support_content
        if login_password:
            masked_content = re.sub(
                r'(Password:\s*)' + re.escape(login_password),
                r'\1' + '*' * len(login_password),
                masked_content
            )
        st.write(masked_content)

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🤖 **GENERATE CODE NOW**", type="primary", use_container_width=True):
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

                with st.spinner("Generating code... This may take a few minutes."):
                    payload = {
                        "project_name": proj["project_name"],
                        "language": proj["project_lang"],
                        "framework": proj["project_fw"],
                        "project_path": proj.get("project_path", ""),
                        "bdd_content": bdd_content,
                        "support_content": support_content
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
                        st.error(f"❌ **Backend error**")

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

            for key in ["generated_result", "show_save_section", "selected_project"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.cache_data.clear()
            time.sleep(3)
            st.rerun()
        if failed:
            for error in failed:
                st.error(f"❌ {error}")


# =========================
# MAIN APP
# =========================
def run_app():
    init_db()
    st.set_page_config(page_title="AI QA Agent", layout="wide")
    st.title("**Convert BDD files to automation code**")

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
                ❌ Backend unavailable
                </div>
                """, unsafe_allow_html=True)

    for key in ["generated_result", "show_save_section", "selected_project"]:
        if key not in st.session_state:
            st.session_state[key] = None

    st.markdown("---")
    st.markdown("### **Choose Action**")
    mode = st.radio("", ["Create New Project", "Select Existing Project"])

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

    with st.expander("**Click here to get Database View**", expanded=False):
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
