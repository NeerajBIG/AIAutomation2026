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
# INSTALL REQUIREMENTS
# -------------------------

def install_requirements(project_path):
    req_file = os.path.join(project_path, "requirements.txt")
    if os.path.exists(req_file):
        st.info("📦 Installing requirements.txt...")
        result = subprocess.run(
            ["pip", "install", "-r", req_file],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            st.success("✅ Requirements installed successfully!")
        else:
            st.error(f"❌ Failed to install requirements:\n{result.stderr}")
        with st.expander("📋 Installation Logs", expanded=False):
            st.code(result.stdout + result.stderr)
    else:
        st.warning(f"⚠️ No requirements.txt found at: {project_path}")


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

def run_live_command(cmd, log_placeholder):

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    output_lines = []

    for line in process.stdout:
        output_lines.append(line)
        log_placeholder.code("".join(output_lines), language="bash")

    process.wait()

    return "".join(output_lines)


# -------------------------
# MAIN APP
# -------------------------

def run_app():

    st.set_page_config(page_title="Test Execution Dashboard", layout="wide")

    st.title("Test Execution Dashboard")

    if "history" not in st.session_state:
        st.session_state.history = []

    projects = get_projects()

    if not projects:
        st.warning("No projects found in database.")
        return

    project_names = [p["project_name"] for p in projects]

    selected_project_name = st.selectbox("Select Project", project_names)

    project = next(p for p in projects if p["project_name"] == selected_project_name)

    project_path = project["project_path"]
    project_fw = project["project_fw"]

    # -------------------------
    # INSTALL REQUIREMENTS
    # -------------------------

    install_requirements(project_path)

    st.markdown("---")

    # -------------------------
    # LOAD TEST FILES
    # -------------------------

    test_files = get_test_files(project_path, project_fw)

    if not test_files:
        st.warning("No tests found.")
        return

    file_map = {os.path.basename(f): f for f in test_files}

    selected_test_name = st.selectbox("Select Test File", list(file_map.keys()))

    selected_test = file_map[selected_test_name]
    report_name = "report.html"

    if project_fw == "Pytest":
        report_name = "pytest_report.html"
    elif project_fw == "Behave":
        report_name = "behave_report.html"

    report_path = os.path.join(project_path, report_name)

    # -------------------------
    # RUN MODE - RADIO + BUTTON
    # -------------------------

    run_mode = st.radio(
        "Select Run Mode",
        options=["▶ Run Selected Test", "🚀 Run All Tests"],
        horizontal=True
    )

    run_button = st.button("▶ Run", use_container_width=True)

    run_single = run_button and run_mode == "▶ Run Selected Test"
    run_all = run_button and run_mode == "🚀 Run All Tests"

    # ===================================================
    # FULL WIDTH CONTAINER
    # ===================================================

    full_width = st.container()

    with full_width:

        st.markdown("---")
        st.markdown("### Test Results")

        m1, m2, m3 = st.columns(3)
        total_ph = m1.empty()
        passed_ph = m2.empty()
        failed_ph = m3.empty()

        st.markdown("### Test Logs")
        cmd_placeholder = st.empty()
        spinner_placeholder = st.empty()
        log_placeholder = st.empty()

        # -------------------------
        # RUN SINGLE TEST
        # -------------------------

        if run_single:

            # Start Time
            start_time = datetime.now()
            start_time_str = start_time.strftime("%H:%M:%S")

            if st.session_state.history:
                if "history" in st.session_state:
                    st.session_state.history = []

            cmd = build_test_command(project_fw, selected_test, report_path)
            cmd_placeholder.code(" ".join(cmd))

            with spinner_placeholder.container():
                with st.spinner("Running test..."):
                    output = run_live_command(cmd, log_placeholder)

            total, passed, failed = parse_results(output)

            total_ph.metric("Total", total)
            passed_ph.metric("✅ Passed", passed)
            failed_ph.metric("❌ Failed", failed)

            end_time = datetime.now()
            total_runtime = end_time - start_time
            runtime_str = str(total_runtime).split(".")[0]

            st.session_state.history.append({
                "Project": selected_project_name,
                "Test": selected_test_name,
                "Total": total,
                "Passed": passed,
                "Failed": failed,
                "Time": runtime_str
            })

        # -------------------------
        # RUN ALL TESTS
        # -------------------------

        if run_all:
            if st.session_state.history:
                if "history" in st.session_state:
                    st.session_state.history = []

            if project_fw == "Behave":
                tests_dir = os.path.join(project_path, "features")
            else:
                tests_dir = os.path.join(project_path, "tests")

            cmd = build_test_command(project_fw, tests_dir, report_path)
            cmd_placeholder.code(" ".join(cmd))

            with spinner_placeholder.container():
                with st.spinner("Running full suite..."):
                    output = run_live_command(cmd, log_placeholder)

            total, passed, failed = parse_results(output)

            total_ph.metric("Total", total)
            passed_ph.metric("✅ Passed", passed)
            failed_ph.metric("❌ Failed", failed)

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

            st.markdown("---")

            with st.expander("📊 HTML Report", expanded=False):

                st.success("✅ HTML Report Generated")

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
        # RUN HISTORY
        # -------------------------

        if st.session_state.history:

            st.markdown("---")
            st.markdown("### Run History")
            st.dataframe(
                st.session_state.history,
                use_container_width=True
            )


# -------------------------
# START APP
# -------------------------

if __name__ == "__main__":
    run_app()