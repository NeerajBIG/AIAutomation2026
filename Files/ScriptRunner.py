import os
import subprocess
import streamlit as st


def run_app():
    st.set_page_config(page_title="Script Runner", layout="wide")

    st.title("🧰 Script Runner")

    st.write("Select a Python script and run it.")

    # Get python files in current directory
    scripts = [f for f in os.listdir(".") if f.endswith(".py") and f != os.path.basename(__file__)]

    if not scripts:
        st.warning("No Python scripts found in this directory.")
        return

    selected_script = st.selectbox("Select Script", scripts)

    if st.button("Run Script"):
        try:
            result = subprocess.run(
                ["python", selected_script],
                capture_output=True,
                text=True
            )

            st.subheader("Output")
            st.code(result.stdout if result.stdout else "No output")

            if result.stderr:
                st.subheader("Errors")
                st.code(result.stderr)

        except Exception as e:
            st.error(f"Error running script: {e}")


if __name__ == "__main__":
    run_app()