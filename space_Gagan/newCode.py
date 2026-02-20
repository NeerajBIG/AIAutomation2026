import streamlit as st
import os, sqlite3, requests, pandas as pd
from datetime import datetime
import time
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("qa_agent.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS ProjectDetails (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    project_name TEXT UNIQUE, lang TEXT, fw TEXT, path TEXT, created_date TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS BDDDetails (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    file_name TEXT, file_content TEXT, created_date TEXT, project_id INTEGER)""")

    # Auto-migrate: Check for 'path' column
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(ProjectDetails)")
    if 'path' not in [c[1] for c in cursor.fetchall()]:
        cursor.execute("ALTER TABLE ProjectDetails ADD COLUMN path TEXT")
    conn.commit()
    conn.close()


init_db()


def get_db():
    conn = sqlite3.connect("qa_agent.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

db = get_db()
projects = [dict(p) for p in db.execute("SELECT * FROM ProjectDetails").fetchall()]
project_names = [p['project_name'] for p in projects]
with st.container(border=True):
    st.markdown("<h1 style='text-align: center;'>🤖 AI QA Agent</h1>", unsafe_allow_html=True)
    st.set_page_config(page_title="🤖 AI QA Agent", layout="wide")
    # st.title("🤖 AI QA Agent")
    # mode = st.radio("Choose Mode", ["Select Existing Project", "Create New Project"], horizontal=True)

    if not projects:
        st.warning("⚠️ No Project Available. \nPlease Create New Project")
        mode = st.radio("Action:", ["Create New Project"])
    else:
        mode = st.radio("Action:", ["Select Existing Project", "Create New Project"])
    # --- CREATE PROJECT ---
    if mode == "Create New Project":
        # with st.container(border=True):

        st.subheader("🛠️ Initialize Project Structure")
        p_name = st.text_input("Project Name")
        c1, c2 = st.columns(2)
        lang = c1.selectbox("Language", ["Python", "Java", "C#"])
        fw = c2.selectbox("Framework", ["Pytest", "Behave"] if lang == "Python" else ["Cucumber", "TestNG"])
        p_path = st.text_input("Local System Path", value="C:/QA_Automation")

        if st.button("🚀 Create Project"):
            if p_name and p_path:
                error_occured = False
                try:
                    payload = {"project_name": p_name, "language": lang, "framework": fw, "project_path": p_path}
                    res = requests.post("http://127.0.0.1:8000/build-structure", data=payload)

                    if res.status_code == 200:
                        db.execute(
                            "INSERT INTO ProjectDetails (project_name, lang, fw, path, created_date) VALUES (?,?,?,?,?)",
                            (p_name, lang, fw, p_path, datetime.now().strftime("%Y-%m-%d"))
                        )
                        db.commit()
                        st.success("✅ Project Structure Created!")
                        st.toast('Project Created Successfully!', icon='🚀')

                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"Backend Error: {res.text}")
                        error_occured = True
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Backend Not Connected! Please check if your FastAPI is running.")
                    error_occured = True
                except Exception as e:
                    if not str(e).strip() == "":
                        st.error(f"Project Already Exists With Same Name")

    # --- SELECT PROJECT ---
    elif mode == "Select Existing Project" and project_names:
        sel_proj = st.selectbox("Choose Project", project_names)
        proj = next(p for p in projects if p['project_name'] == sel_proj)
        p_id = proj['project_id']
        p_path_val = proj.get('path', 'C:/QA_Automation')

        # st.info(f"📍 Location: {p_path_val}/{proj['project_name']}")

        if 'modify' not in st.session_state: st.session_state.modify = False
        if 'create' not in st.session_state: st.session_state.create = False


        def t_m():
            st.session_state.create = False

        def t_c():
            st.session_state.modify = False


        col1, col2 = st.columns(2)
        with col1:

            st.checkbox("Modify Existing Files", key="modify", on_change=t_m)
        with col2:
            st.checkbox("Upload New Files", key="create", on_change=t_c)

        if st.session_state.modify:
            files = db.execute("SELECT * FROM BDDDetails WHERE project_id = ?", (p_id,)).fetchall()
            if files:
                f_names = list(set([f['file_name'] for f in files]))
                sel_f = st.selectbox("Select File", f_names)
                curr_f = [f for f in files if f['file_name'] == sel_f][-1]
                edit_name = st.text_input("Enter New Name)", value=curr_f['file_name'])
                edit_content = st.text_area("File Editor", value=curr_f['file_content'], height=250)

                if st.button("🚀 Update File & Generate Code"):
                    db.execute(
                        "INSERT INTO BDDDetails (file_name, file_content, created_date, project_id) VALUES (?,?,?,?)",
                        (sel_f, edit_content, datetime.now().strftime("%H:%M:%S"), p_id))
                    db.commit()

                    with st.spinner("🤖 Analyzing structure and Writing code..."):
                        payload = {
                            "project_name": proj['project_name'], "language": proj['lang'],
                            "framework": proj['fw'], "project_path": p_path_val,
                            "bdd_content": edit_content
                        }
                        try:
                            res = requests.post("http://127.0.0.1:8000/generate-agent-code", data=payload, timeout=180)
                            if res.status_code == 200:
                                st.success("✅ File updated and Code synced to local folders!")
                                with st.expander("Agent Report"):
                                    st.write(res.json().get('agent_report'))
                            else:
                                st.error(f"FIle already exists with same content. Please Update the file content.")
                        except:
                            st.error("🔌 Backend Not Connected!")
            else:
                st.info("No file available. Please upload new files")

        if st.session_state.create:
            up_files = st.file_uploader("Upload Requirements / BDD Files", accept_multiple_files=True)

            if st.button("🚀 Upload File & Generate Code"):
                if up_files:
                    all_files_data = {}

                    for f in up_files:
                        content = f.read().decode("utf-8")
                        f_name = os.path.splitext(f.name)[0]

                        all_files_data[f_name] = content

                        db.execute(
                            "INSERT INTO BDDDetails (file_name, file_content, created_date, project_id) VALUES (?,?,?,?)",
                            (f_name, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), p_id))

                    db.commit()

                    with st.spinner(f"🤖 Processing {len(up_files)} Files..."):
                        payload = {
                            "project_name": proj['project_name'],
                            "language": proj['lang'],
                            "framework": proj['fw'],
                            "project_path": p_path_val,
                            "bdd_content": json.dumps(all_files_data)
                        }
                        try:
                            res = requests.post("http://127.0.0.1:8000/generate-agent-code", data=payload, timeout=300)
                            if res.status_code == 200:
                                st.success(f"✅ All {len(up_files)} files processed and synced!")
                                with st.expander("Agent Report"):
                                    st.write(res.json().get('agent_report'))
                            else:
                                st.error(f"API issue")
                        except Exception as e:
                            st.error(f"🔌 Backend Connection Error: {str(e)}")
                else:
                    st.warning("Please upload at least one file.")


# --- DATABASE VIEW ---
st.divider()
with st.container(border=True):
    if st.checkbox("📊 Database View "):
        conn = sqlite3.connect("qa_agent.db")
        st.write("### Project Details")
        st.dataframe(pd.read_sql_query("SELECT * FROM ProjectDetails", conn), use_container_width=True)
        st.write("### File Details")
        st.dataframe(pd.read_sql_query("SELECT * FROM BDDDetails", conn), use_container_width=True)
        conn.close()

# st.caption("System: CrewAI + Streamlit | Framework Builder v2.0")
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>"
            "System: CrewAI + Streamlit | Framework Builder | "
            "<span style='background-color: #1B9CFC; color: yellow; padding: 2px 8px; border-radius: 10px; font-weight: bold;'>"
            "Developed by Gagandeep Singh</span></div>", unsafe_allow_html=True)