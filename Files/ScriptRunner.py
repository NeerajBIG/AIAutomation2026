import os
import subprocess
import sqlite3
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
import re
import webbrowser

load_dotenv()

DB_NAME = os.getenv("LOCAL_DB_NAME")
DB_FILE = DB_NAME + ".db"


# -------------------------
# DATABASE
# -------------------------

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_projects():
    db = get_db()
    rows = db.execute("SELECT * FROM ProjectDetails").fetchall()
    return [dict(r) for r in rows]


# -------------------------
# TEST FILE DISCOVERY
# -------------------------

def get_test_files(project_path, framework):

    if framework == "Behave":
        tests_dir = os.path.join(project_path, "features")
    else:
        tests_dir = os.path.join(project_path, "tests")

    if not os.path.exists(tests_dir):
        return []

    files = []

    for root, dirs, filenames in os.walk(tests_dir):

        for f in filenames:

            if framework == "Pytest":

                if f.startswith("test_") and f.endswith(".py"):
                    files.append(os.path.join(root, f))

            elif framework == "Behave":

                if f.endswith(".feature"):
                    files.append(os.path.join(root, f))

            else:

                if f.endswith(".py") and f != "__init__.py":
                    files.append(os.path.join(root, f))

    return files


# -------------------------
# COMMAND BUILDER
# -------------------------

def build_test_command(framework, path, report_file=None):

    if framework == "Pytest":

        cmd = ["pytest", path, "-v"]

        if report_file:
            cmd += ["--html", report_file, "--self-contained-html"]

        return cmd

    elif framework == "Behave":

        cmd = ["behave", path]

        if report_file:
            cmd += ["-f", "html", "-o", report_file]

        return cmd

    else:

        return ["python", path]


# -------------------------
# METRICS PARSER
# -------------------------

def parse_results(output):

    passed = len(re.findall(r"PASSED", output))
    failed = len(re.findall(r"FAILED", output))
    skipped = len(re.findall(r"SKIPPED", output))

    total = passed + failed + skipped

    return total, passed, failed


# -------------------------
# LIVE COMMAND RUNNER
# -------------------------

def run_live_command(cmd):

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    output_lines = []
    placeholder = st.empty()

    for line in process.stdout:
        output_lines.append(line)
        placeholder.code("".join(output_lines))

    process.wait()

    return "".join(output_lines)


# -------------------------
# MAIN APP
# -------------------------

def run_app():

    st.set_page_config(page_title="Test Execution Dashboard", layout="wide")

    st.title("🧪 Test Execution Dashboard")

    if "history" not in st.session_state:
        st.session_state.history = []

    projects = get_projects()

    if not projects:
        st.warning("No projects found in database.")
        return

    project_names = [p["project_name"] for p in projects]

    selected_project_name = st.selectbox(
        "Select Project",
        project_names
    )

    project = next(p for p in projects if p["project_name"] == selected_project_name)

    project_path = project["project_path"]
    project_fw = project["project_fw"]

    # -------------------------
    # LOAD TEST FILES
    # -------------------------

    test_files = get_test_files(project_path, project_fw)

    if not test_files:
        st.warning("No tests found.")
        return

    file_map = {os.path.basename(f): f for f in test_files}

    selected_test_name = st.selectbox(
        "Select Test File",
        list(file_map.keys())
    )

    selected_test = file_map[selected_test_name]

    col1, col2 = st.columns(2)

    report_name = "report.html"

    if project_fw == "Pytest":
        report_name = "pytest_report.html"

    elif project_fw == "Behave":
        report_name = "behave_report.html"

    report_path = os.path.join(project_path, report_name)

    # -------------------------
    # RUN SINGLE TEST
    # -------------------------

    with col1:

        if st.button("▶ Run Selected Test", use_container_width=True):

            cmd = build_test_command(project_fw, selected_test, report_path)

            st.code(" ".join(cmd))

            with st.spinner("Running test..."):
                output = run_live_command(cmd)

            total, passed, failed = parse_results(output)

            m1, m2, m3 = st.columns(3)

            m1.metric("Total", total)
            m2.metric("Passed", passed)
            m3.metric("Failed", failed)

            st.session_state.history.append({
                "Project": selected_project_name,
                "Test": selected_test_name,
                "Total": total,
                "Passed": passed,
                "Failed": failed,
                "Time": datetime.now().strftime("%H:%M:%S")
            })

            with st.expander("📄 Test Logs", expanded=True):
                st.code(output)

    # -------------------------
    # RUN ALL TESTS
    # -------------------------

    with col2:

        if st.button("🚀 Run All Tests", use_container_width=True):

            if project_fw == "Behave":
                tests_dir = os.path.join(project_path, "features")
            else:
                tests_dir = os.path.join(project_path, "tests")

            cmd = build_test_command(project_fw, tests_dir, report_path)

            st.code(" ".join(cmd))

            with st.spinner("Running full suite..."):
                output = run_live_command(cmd)

            total, passed, failed = parse_results(output)

            m1, m2, m3 = st.columns(3)

            m1.metric("Total", total)
            m2.metric("Passed", passed)
            m3.metric("Failed", failed)

            st.session_state.history.append({
                "Project": selected_project_name,
                "Test": "ALL_TESTS",
                "Total": total,
                "Passed": passed,
                "Failed": failed,
                "Time": datetime.now().strftime("%H:%M:%S")
            })

    # -------------------------
    # HTML REPORT VIEWER
    # -------------------------

    if os.path.exists(report_path):

        with st.expander("📊 HTML Report"):

            st.success("HTML Report Generated")

            c1, c2 = st.columns(2)

            with c1:
                if st.button("🌐 Open Report"):
                    webbrowser.open(report_path)

            with c2:
                with open(report_path, "rb") as f:
                    st.download_button(
                        "⬇ Download Report",
                        f,
                        file_name=os.path.basename(report_path),
                        mime="text/html"
                    )


# -------------------------
# START APP
# -------------------------

if __name__ == "__main__":
    run_app()