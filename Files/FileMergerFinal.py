import os
import time
from streamlit_js_eval import streamlit_js_eval
import streamlit as st
import html

def run_app():
    st.set_page_config(page_title="Colorful Dual File Editor", layout="wide")

    # -------- SESSION STATE INIT --------
    for key in ["file1_text", "file2_text", "file1_uploaded", "file2_uploaded"]:
        if key not in st.session_state:
            st.session_state[key] = ""

    if "file2_load_counter" not in st.session_state:
        st.session_state.file2_load_counter = 0

    # -------- CSS --------
    st.markdown("""
    <style>
    .file-header-left { 
        background: linear-gradient(90deg, #ff6b6b, #ff8e8e); 
        padding: 8px 12px; border-radius: 6px; font-weight: 600; color: white; 
        text-align: center; margin-bottom: 10px;
    }
    .file-header-right { 
        background: linear-gradient(90deg, #4ecdc4, #6be2d8); 
        padding: 8px 12px; border-radius: 6px; font-weight: 600; color: white; 
        text-align: center; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("Manual File Editor with Line Comparison")

    col1, col2 = st.columns(2)

    # -------- LEFT FILE --------
    with col1:
        st.markdown("<div class='file-header-left'>Upgraded File</div>", unsafe_allow_html=True)
        uploaded_file1 = st.file_uploader("Browse Upgraded File", key="file1_uploader_key")

        if uploaded_file1 is not None:
            if st.button("Show Right Side Panel", key="load_file1_button"):
                st.text("    ")
                st.session_state.file1_text = uploaded_file1.getvalue().decode("utf-8", errors="ignore")
                st.session_state.file1_uploaded = uploaded_file1.name
                st.rerun()

    # -------- RIGHT FILE --------
    with col2:
        if st.session_state.file1_text:  # show only after File 1 is loaded
            st.markdown("<div class='file-header-right'>File to Modify</div>", unsafe_allow_html=True)
            uploaded_file2 = st.file_uploader("Browse File to Modify", key="file2_uploader_key")

            if uploaded_file2 is not None:
                if st.button("Compare Files", key="load_file2_button"):
                    new_text = uploaded_file2.getvalue().decode("utf-8", errors="ignore")
                    st.session_state.file2_text = new_text
                    st.session_state.file2_uploaded = uploaded_file2.name
                    st.session_state.file2_load_counter += 1
                    st.rerun()

    # -------- INLINE STYLE CONSTANTS --------
    MATCHED_STYLE = "background-color:#006400; color:#ffffff;"
    UNMATCHED_STYLE = "background-color:#ff4d4d; color:#000000;"
    LINE_NUM_STYLE = "color:#ccc; display:inline-block; width:40px; text-align:right; padding-right:10px; user-select:none; flex-shrink:0;"

    col1, col2 = st.columns(2)

    # -------- LEFT DIFF VIEW --------
    with col1:
        st.text("      ")
        st.text("      ")
        st.text("      ")
        if st.session_state.file1_text and st.session_state.file2_text:
            file1_lines = st.session_state.file1_text.splitlines()
            file2_lines = st.session_state.file2_text.splitlines()
            max_lines = max(len(file1_lines), len(file2_lines), 1)

            rows_html = ""
            for i in range(max_lines):
                line1 = file1_lines[i] if i < len(file1_lines) else ""
                line2 = file2_lines[i] if i < len(file2_lines) else ""
                style = MATCHED_STYLE if line1 == line2 else UNMATCHED_STYLE
                rows_html += (
                    f"<div style='display:flex; width:100%; box-sizing:border-box; padding:2px 5px; {style}'>"
                    f"<span style='{LINE_NUM_STYLE}'>{i + 1}</span>"
                    f"<span style='flex:1; min-width:0; white-space:pre; font-family:monospace; font-size:13px; background-color:inherit; color:inherit;'>"
                    f"{html.escape(line1)}"
                    f"</span>"
                    f"</div>"
                )

            st.markdown(
                f"""
                <div style="overflow-x:auto; width:100%;">
                    <div style="min-width:max-content; width:100%;">
                        {rows_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            pass
            st.text("   ")
            # st.info("Load File 1 to see comparison.")

    # -------- RIGHT PANEL --------
    with col2:

        # NEW CHECKBOX (does not affect existing logic)
        if st.session_state.file1_text and st.session_state.file2_text:
            enable_edit = st.checkbox("✏️ Enable editing for File 2")

            if enable_edit:

                editor_key = f"file2_editor_area_{st.session_state.file2_load_counter}"

                line_count = len(st.session_state.file2_text.splitlines())
                auto_height = max(200, line_count * 27 + 60)

                # Override Streamlit's internal max-height cap and remove vertical scroll
                st.markdown(
                    f"<style>[data-testid='stTextArea'] textarea "
                    f"{{ height:{auto_height}px !important; max-height:none !important; "
                    f"overflow-y:hidden !important; resize:none !important; }}</style>",
                    unsafe_allow_html=True
                )

                edited_text = st.text_area(
                    label="Edit File 2",
                    label_visibility="collapsed",
                    value=st.session_state.file2_text,
                    height=auto_height,
                    key=editor_key
                )

                if edited_text != st.session_state.file2_text:
                    st.session_state.file2_text = edited_text

            else:
                file1_lines = st.session_state.file1_text.splitlines()
                file2_lines = st.session_state.file2_text.splitlines()
                max_lines   = max(len(file1_lines), len(file2_lines), 1)

                rows_html = ""
                for i in range(max_lines):
                    line1 = file1_lines[i] if i < len(file1_lines) else ""
                    line2 = file2_lines[i] if i < len(file2_lines) else ""
                    style = MATCHED_STYLE if line1 == line2 else UNMATCHED_STYLE
                    rows_html += (
                        f"<div style='display:flex; width:100%; box-sizing:border-box; padding:2px 5px; {style}'>"
                        f"<span style='{LINE_NUM_STYLE}'>{i+1}</span>"
                        f"<span style='flex:1; min-width:0; white-space:pre; font-family:monospace; font-size:13px; background-color:inherit; color:inherit;'>"
                        f"{html.escape(line2)}"
                        f"</span>"
                        f"</div>"
                    )
                st.markdown(
                    f"""
                    <div style="overflow-x:auto; border:1px solid #ddd; width:100%;">
                        <div style="min-width:max-content; width:100%;">
                            {rows_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # -------- SAVE FILE 2 --------
    if st.session_state.file2_text:
        st.divider()
        folder_path = st.text_input(
            "Folder to save Modified File",
            value=os.path.expanduser("~/Documents/ColorfulEditorOutput"),
            key="folder_path_key"
        )
        file_name = st.text_input(
            "Filename for Modified File",
            value=st.session_state.file2_uploaded or "file2_edited.py",
            key="file_name_key"
        )
        save_location2 = os.path.join(folder_path, file_name)

        if st.button("💾 Save Modified File", key="save_file2_button_key"):
            try:
                os.makedirs(folder_path, exist_ok=True)
                with open(save_location2, "w", encoding="utf-8") as f:
                    f.write(st.session_state.file2_text)
                st.success(f"✅ Saved File at: {save_location2}")
                time.sleep(3)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
            except PermissionError:
                st.error("❌ Permission denied. Please choose a different folder.")
            except Exception as e:
                st.error(f"❌ Error saving file: {str(e)}")


if __name__ == "__main__":
    run_app()