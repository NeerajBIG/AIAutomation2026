import os
import streamlit as st
import html
import difflib

# -------- TEMPLATES PER FILE TYPE + ACTION --------
TEMPLATES = {
    "Pytest (.py)": {
        "Add a new test case": (
            "\ndef test_new_case():\n"
            "    # TODO: implement test\n"
            "    assert True\n"
        ),
        "Remove a test case": None,
        "Add an import": "import pytest\n",
    },
    "Behave (.feature)": {
        "Add a new test case": (
            "\n  Scenario: New scenario\n"
            "    Given a precondition\n"
            "    When an action is performed\n"
            "    Then the result should be expected\n"
        ),
        "Remove a test case": None,
        "Add an import": "# @import: module_name\n",
    },
    "TypeScript (.ts / .tsx)": {
        "Add a new test case": (
            "\nit('should do something', () => {\n"
            "  // TODO: implement test\n"
            "  expect(true).toBe(true);\n"
            "});\n"
        ),
        "Remove a test case": None,
        "Add an import": "import {  } from '';\n",
    },
}

ACTIONS = ["Add a new test case", "Remove a test case", "Add an import"]


def apply_modification(original_text, action, line_number, custom_snippet=None):
    lines = original_text.splitlines()
    total = len(lines)
    errors = []

    if line_number < 1 or line_number > total:
        errors.append(f"Line number {line_number} is out of range (file has {total} lines).")
        return original_text, errors

    idx = line_number - 1

    if action in ("Add a new test case", "Add an import"):
        snippet = custom_snippet or ""
        snippet_lines = snippet.splitlines(keepends=False)
        new_lines = lines[:idx] + snippet_lines + lines[idx:]
        return "\n".join(new_lines), errors

    elif action == "Remove a test case":
        new_lines = lines[:idx] + lines[idx + 1:]
        return "\n".join(new_lines), errors

    return original_text, errors


def build_file_view_html(lines, style="unchanged"):
    """Build an HTML view of file lines with line numbers (no diff coloring)."""
    rows_html = ""
    LINE_NUM_STYLE = "color:#444; display:inline-block; width:36px; text-align:right; padding-right:12px; user-select:none; flex-shrink:0; font-size:11px;"
    for i, line in enumerate(lines):
        rows_html += (
            f"<div style='display:flex; width:100%; padding:2px 14px; background-color:#0d1117; color:#c9d1d9;'>"
            f"<span style='{LINE_NUM_STYLE}'>{i+1}</span>"
            f"<span style='flex:1; min-width:0; white-space:pre; font-family:JetBrains Mono,monospace; font-size:12.5px;'>"
            f"{html.escape(line)}"
            f"</span>"
            f"</div>"
        )
    return rows_html


def build_diff_html(orig_lines, mod_lines):
    matcher = difflib.SequenceMatcher(None, orig_lines, mod_lines)
    left_rows  = []
    right_rows = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                left_rows.append((i1+k+1, orig_lines[i1+k], "unchanged"))
                right_rows.append((j1+k+1, mod_lines[j1+k], "unchanged"))
        elif tag == "replace":
            lb = [(i1+k+1, orig_lines[i1+k], "removed") for k in range(i2-i1)]
            rb = [(j1+k+1, mod_lines[j1+k], "added")   for k in range(j2-j1)]
            while len(lb) < len(rb): lb.append((None, "", "empty"))
            while len(rb) < len(lb): rb.append((None, "", "empty"))
            left_rows.extend(lb); right_rows.extend(rb)
        elif tag == "delete":
            for k in range(i2 - i1):
                left_rows.append((i1+k+1, orig_lines[i1+k], "removed"))
                right_rows.append((None, "", "empty"))
        elif tag == "insert":
            for k in range(j2 - j1):
                left_rows.append((None, "", "empty"))
                right_rows.append((j1+k+1, mod_lines[j1+k], "added"))

    rows_html = ""
    for (ln, lt, ls), (rn, rt, rs) in zip(left_rows, right_rows):
        lnum = f"<span class='line-num'>{ln}</span>" if ln else "<span class='line-num'></span>"
        rnum = f"<span class='line-num'>{rn}</span>" if rn else "<span class='line-num'></span>"
        rows_html += (
            f"<div class='diff-row'>"
            f"<div class='diff-cell {ls}'>{lnum}{html.escape(lt)}</div>"
            f"<div class='diff-cell {rs}'>{rnum}{html.escape(rt)}</div>"
            f"</div>"
        )
    added_count   = sum(1 for _, _, s in right_rows if s == "added")
    removed_count = sum(1 for _, _, s in left_rows  if s == "removed")
    return rows_html, added_count, removed_count


def run_app():
    st.set_page_config(page_title="File Modifier", layout="wide")

    # -------- SESSION STATE INIT --------
    defaults = {
        "original_text": "",
        "modified_text": "",
        "uploaded_filename": "",
        "apply_error": "",
        "custom_snippet": "",
        "iteration": 0,
        "base_text": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # -------- CSS --------
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

    .main-title {
        font-family: 'Syne', sans-serif; font-weight: 800; font-size: 2.2rem;
        letter-spacing: -1px;
        background: linear-gradient(90deg, #00c6ff, #0072ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .panel-header {
        font-family: 'Syne', sans-serif; font-weight: 700; font-size: 0.72rem;
        letter-spacing: 2px; text-transform: uppercase; color: #888;
        padding: 8px 14px; background: #1a1a2e; border: 1px solid #2a2a2a;
        border-bottom: none; border-radius: 8px 8px 0 0;
    }
    .file-view-container {
        border: 1px solid #2a2a2a; border-radius: 0 0 8px 8px;
        overflow-x: auto; font-family: 'JetBrains Mono', monospace;
    }
    .diff-container {
        font-family: 'JetBrains Mono', monospace; font-size: 12.5px;
        border-radius: 8px; overflow: hidden; border: 1px solid #2a2a2a; margin-top: 4px;
    }
    .diff-header { display: flex; background: #1a1a2e; border-bottom: 1px solid #2a2a2a; }
    .diff-header-cell {
        flex: 1; padding: 8px 14px; font-family: 'Syne', sans-serif; font-size: 0.72rem;
        font-weight: 600; letter-spacing: 2px; text-transform: uppercase;
        color: #888; border-right: 1px solid #2a2a2a;
    }
    .diff-header-cell:last-child { border-right: none; }
    .diff-row { display: flex; width: 100%; border-bottom: 1px solid #1a1a1a; }
    .diff-cell {
        flex: 1; padding: 2px 14px; white-space: pre; border-right: 1px solid #1a1a1a;
        min-width: 0; font-family: 'JetBrains Mono', monospace; font-size: 12.5px;
    }
    .diff-cell:last-child { border-right: none; }
    .line-num {
        display: inline-block; width: 36px; text-align: right;
        padding-right: 12px; color: #444; user-select: none; flex-shrink: 0; font-size: 11px;
    }
    .unchanged { background-color: #0d1117; color: #c9d1d9; }
    .added     { background-color: #0d2a1a; color: #56d364; }
    .removed   { background-color: #2a0d0d; color: #f87171; }
    .empty     { background-color: #0d1117; color: transparent; }
    .stats-bar { display: flex; gap: 16px; padding: 10px 0; margin-bottom: 4px; flex-wrap: wrap; }
    .stat-chip {
        padding: 4px 12px; border-radius: 20px;
        font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 600;
    }
    .stat-added   { background: #0d2a1a; color: #56d364; border: 1px solid #1a4a2a; }
    .stat-removed { background: #2a0d0d; color: #f87171; border: 1px solid #4a1a1a; }
    .stat-total   { background: #1a1a2e; color: #7ea8ff; border: 1px solid #2a2a4e; }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stNumberInput"] label,
    div[data-testid="stFileUploader"] label,
    div[data-testid="stTextArea"] label {
        font-family: 'Syne', sans-serif !important; font-weight: 600 !important;
        font-size: 0.78rem !important; letter-spacing: 1.5px !important;
        text-transform: uppercase !important; color: #aaa !important;
    }
    div[data-testid="stButton"] button {
        background: linear-gradient(90deg, #0072ff, #00c6ff);
        color: white; border: none; font-family: 'Syne', sans-serif;
        font-weight: 600; letter-spacing: 1px; border-radius: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("**File Modifier**")
    # st.markdown("<div class='main-title'>File Modifier</div>", unsafe_allow_html=True)
    # st.markdown(
    #     "<p style='color:#666; font-size:0.9rem; margin-top:4px; margin-bottom:24px;'>"
    #     "Insert or remove content at a specific line in Pytest, Behave, or TypeScript files</p>",
    #     unsafe_allow_html=True
    # )

    # -------- ROW 1: File type + File upload --------
    col_type, col_file = st.columns([1.5, 2.5])
    with col_type:
        file_type = st.selectbox("File Type", options=list(TEMPLATES.keys()), key="file_type_select")
    with col_file:
        uploaded_file = st.file_uploader(
            "Browse File", type=["py", "feature", "ts", "tsx"], key="file_uploader"
        )
        if uploaded_file is not None:
            decoded = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            if decoded != st.session_state.original_text or uploaded_file.name != st.session_state.uploaded_filename:
                st.session_state.original_text = decoded
                st.session_state.base_text = decoded
                st.session_state.uploaded_filename = uploaded_file.name
                st.session_state.modified_text = ""
                st.session_state.apply_error = ""
                st.session_state.custom_snippet = ""
                st.session_state.iteration = 0

    # -------- ROW 2: Action + Line number --------
    col_action, col_line = st.columns([2, 1])
    with col_action:
        action = st.selectbox("Action", options=ACTIONS, key="action_select")
    with col_line:
        total_lines = len(st.session_state.original_text.splitlines()) if st.session_state.original_text else 1
        line_number = st.number_input(
            "At Line Number", min_value=0, max_value=max(total_lines, 1),
            value=0, step=1, key="line_number_input"
        )

    # -------- SNIPPET EDITOR --------
    snippet_default = TEMPLATES[file_type][action]
    if snippet_default is not None:
        # Reset custom snippet when file type or action changes
        snippet_state_key = f"snippet_{file_type}_{action}"
        if snippet_state_key not in st.session_state:
            st.session_state[snippet_state_key] = snippet_default

        snippet_line_count = len(st.session_state[snippet_state_key].splitlines())
        snippet_height = max(100, snippet_line_count * 22 + 40)

        st.markdown(
            "<style>[data-testid='stTextArea'][aria-label='Snippet to be inserted'] textarea "
            "{ font-family: 'JetBrains Mono', monospace !important; font-size: 12.5px !important; "
            "background: #0d1117 !important; color: #7ea8ff !important; "
            "border: 1px solid #2a2a4e !important; }</style>",
            unsafe_allow_html=True
        )
        edited_snippet = st.text_area(
            "Snippet to be inserted",
            value=st.session_state[snippet_state_key],
            height=snippet_height,
            key=f"snippet_editor_{file_type}_{action}"
        )
        st.session_state[snippet_state_key] = edited_snippet
        active_snippet = edited_snippet
    else:
        active_snippet = None
        st.markdown(
            f"<div style='margin-top:8px; padding:10px 14px; background:#2a0d0d; border:1px solid #4a1a1a; "
            f"border-radius:6px; font-size:0.85rem; color:#f87171;'>"
            f"⚠ <b>Remove a test case</b> will delete line {int(line_number)} from the file.</div>",
            unsafe_allow_html=True
        )

    # -------- APPLY BUTTON + RESET --------
    btn_col, reset_col, iter_col = st.columns([1, 1, 2])
    with btn_col:
        apply_clicked = st.button("▶ Apply", use_container_width=True)
    with reset_col:
        reset_clicked = st.button("↺ Reset to Original", use_container_width=True)
        if reset_clicked and st.session_state.base_text:
            st.session_state.original_text = st.session_state.base_text
            st.session_state.modified_text = ""
            st.session_state.iteration = 0
            st.session_state.apply_error = ""
    with iter_col:
        if st.session_state.iteration > 0:
            st.markdown(
                f"<div style='padding:8px 0; font-family:JetBrains Mono,monospace; font-size:0.8rem; color:#7ea8ff;'>"
                f"✏️ {st.session_state.iteration} modification(s) applied — "
                f"{len(st.session_state.original_text.splitlines())} lines now</div>",
                unsafe_allow_html=True
            )

    if apply_clicked:
        if line_number != 0:
            if not st.session_state.original_text:
                st.session_state.apply_error = "Please upload a file first."
            else:
                modified, errors = apply_modification(
                    st.session_state.original_text, action, int(line_number), active_snippet
                )
                if errors:
                    st.session_state.apply_error = " ".join(errors)
                else:
                    st.session_state.modified_text = modified
                    st.session_state.apply_error = ""
                    # Promote modified -> original for next iteration
                    st.session_state.original_text = modified
                    st.session_state.modified_text = ""
                    st.session_state.iteration += 1
        else:
            st.error("Please reselect the LINE NUMBER")

    if st.session_state.apply_error:
        st.error(st.session_state.apply_error)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # -------- FILE VIEW: always show original; show diff after apply --------
    if st.session_state.original_text:
        orig_lines = st.session_state.original_text.splitlines()

        if st.session_state.modified_text:
            # ---- DIFF VIEW (after Apply) ----
            mod_lines = st.session_state.modified_text.splitlines()
            rows_html, added_count, removed_count = build_diff_html(orig_lines, mod_lines)

            st.markdown(
                f"<div class='stats-bar'>"
                f"<span class='stat-chip stat-total'>📄 {len(orig_lines)} original lines</span>"
                f"<span class='stat-chip stat-added'>+{added_count} lines added</span>"
                f"<span class='stat-chip stat-removed'>−{removed_count} lines removed</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"""
                <div class='diff-container'>
                    <div class='diff-header'>
                        <div class='diff-header-cell'>Original — {st.session_state.uploaded_filename}</div>
                        <div class='diff-header-cell'>Modified</div>
                    </div>
                    <div style='overflow-x:auto;'>
                        <div style='min-width:max-content; width:100%;'>
                            {rows_html}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            base, ext = os.path.splitext(st.session_state.uploaded_filename)
            st.download_button(
                label="⬇ Download Modified File",
                data=st.session_state.modified_text.encode("utf-8"),
                file_name=f"{base}_modified{ext}",
                mime="text/plain"
            )

        else:
            # ---- ORIGINAL ONLY VIEW (before Apply) ----
            orig_rows_html = build_file_view_html(orig_lines)
            st.markdown(
                f"<div class='panel-header'>📄 Original — {st.session_state.uploaded_filename}</div>"
                f"<div class='file-view-container'>"
                f"<div style='overflow-x:auto;'>"
                f"<div style='min-width:max-content; width:100%;'>{orig_rows_html}</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            "<div style='margin-top:32px; padding:32px; text-align:center; border:1px dashed #2a2a2a; "
            "border-radius:10px; color:#555;'>"
            "<div style='font-size:2rem;'>📂</div>"
            "<div style='font-family:Syne,sans-serif; font-size:0.9rem; margin-top:8px;'>Upload a file to get started</div>"
            "</div>",
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    run_app()