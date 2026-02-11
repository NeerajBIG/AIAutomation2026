import streamlit as st
import subprocess
import socket
import platform
import time

st.set_page_config(page_title="BitsInGlass Automation Tool", page_icon="🤖")

# Header
st.markdown(
    """
    <h1 style='text-align:center; color:#036;'>
        🤖 Welcome to BitsInGlass Automated Tool powered by AI
    </h1>
    <p style='text-align:center; font-size:18px;'>
        Manage and run Locust performance tests with ease.
    </p>
    """,
    unsafe_allow_html=True
)

LOCUST_PORT = 8089
LOCUST_FILE = "../../files/PartnerRe_Locust.py"


# ---------------------------------------------------
# Port Check
# ---------------------------------------------------
def is_port_in_use(port):
    """Check if a specific port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


# ---------------------------------------------------
# Kill Process on Port
# ---------------------------------------------------
def kill_process_on_port(port):
    """Kill any process using the port"""
    system_platform = platform.system().lower()
    try:
        if system_platform == "windows":
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True
            )

            if result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                pids = {line.split()[-1] for line in lines if len(line.split()) >= 5}

                for pid in pids:
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True)

                return True

            return False

        else:
            result = subprocess.run(
                f"lsof -ti:{port}",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    subprocess.run(f"kill -9 {pid}", shell=True)
                return True

            return False

    except Exception as e:
        st.error(f"Error killing process on port {port}: {e}")
        return False


# ---------------------------------------------------
# Start Locust With Animations
# ---------------------------------------------------
def start_locust_with_animation():
    placeholder = st.empty()

    # Step 1 — Check if Locust already running
    if is_port_in_use(LOCUST_PORT):
        with placeholder.container():
            st.warning("⚠️ Existing Locust instance detected on port 8089.")
            st.info("Attempting to stop the existing Locust server...")
            st.progress(30)
            time.sleep(0.5)

        killed = kill_process_on_port(LOCUST_PORT)

        if killed:
            with placeholder.container():
                st.success("🛑 Existing Locust instance stopped successfully!")
                st.balloons()
                time.sleep(1)
        else:
            st.error("Could not kill the previous Locust instance. Try running as admin.")
            return

    # Step 2 — Show animation for starting Locust
    with placeholder.container():
        st.info("🚀 Preparing to start Locust...")
        progress = st.progress(0)
        for i in range(0, 101, 10):
            progress.progress(i)
            time.sleep(0.1)

    # Step 3 — Start Locust
    subprocess.Popen(["locust", "-f", LOCUST_FILE])

    with placeholder.container():
        st.success("🎉 Locust started successfully!")
        st.markdown(
            """
            <p style='font-size:18px;'>
                🌐 <b>Access Locust here:</b>  
                <a href='http://localhost:8089' target='_blank'>http://localhost:8089</a>
            </p>
            """,
            unsafe_allow_html=True
        )


# ---------------------------------------------------
# Button UI
# ---------------------------------------------------
st.markdown("<br><br>", unsafe_allow_html=True)

if st.button("▶️ Start Locust Test", use_container_width=True):
    start_locust_with_animation()
