import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import io
import traceback
import atexit
import re


XPATH_RULE_OPTIONS = [
    "Text-based XPath",
    "ID-based XPath",
    "Name attribute",
    "Unique attributes",
    "CSS Selector",
    ]

DEFAULT_ELEMENT_TYPES = """- input
- button
- a
- select
- textarea
- span
- div
- svg
- tr
"""

REQUIRED_COLUMNS = ["tag", "text", "locator", "unique"]

def parse_element_types(element_types_text: str):
    elements = []
    for line in element_types_text.split("\n"):
        line = line.strip()
        if line.startswith("-"):
            elements.append(line[1:].strip().lower())
    return elements or ["button", "a", "input", "select", "textarea", "span", "div"]


def build_xpath_query(element_types):
    if not element_types:
        return "//*"
    conditions = [f"self::{elem}" for elem in element_types]
    return f"//*[{ ' or '.join(conditions) }]"


def build_priority_xpath(driver, element, rule_order):
    try:
        element_text = element.text.strip()
        element_id = element.get_attribute("id") or ""
        element_name = element.get_attribute("name") or ""
        element_tag = element.tag_name
        element_type = element.get_attribute("type") or ""
        element_class = element.get_attribute("class") or ""
    except Exception:
        return None

    for rule in rule_order:
        if rule == "Text-based XPath" and element_text and len(element_text) < 50:
            clean_text = element_text.replace("'", "\\'")
            return f"//{element_tag}[text()='{clean_text}']"

        if rule == "ID-based XPath" and element_id:
            return f"//{element_tag}[@id='{element_id}']"

        if rule == "Name attribute" and element_name:
            return f"//{element_tag}[@name='{element_name}']"

        if rule == "Unique attributes" and element_type:
            return f"//{element_tag}[@type='{element_type}']"

        if rule == "CSS Selector":
            if element_id:
                return f"#{element_id}"
            elif element_class:
                class_selector = ".".join(
                    [cls for cls in element_class.split() if cls]
                )
                return f"{element_tag}.{class_selector}" if class_selector else None
    return None

def capture_xpaths(
    driver,
    rule_order,
    element_types_text=None,
    require_displayed=True,
    ):
    element_types = parse_element_types(element_types_text or DEFAULT_ELEMENT_TYPES)
    xpath_query = build_xpath_query(element_types)

    try:
        elements = driver.find_elements(By.XPATH, xpath_query)
    except Exception:
        elements = []

    records = []
    seen = set()
    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(elements) if elements else 1

    for idx, el in enumerate(elements):
        try:
            if require_displayed and not el.is_displayed():
                continue

            locator = build_priority_xpath(driver, el, rule_order)
            if not locator or locator in seen:
                continue

            try:
                if locator.startswith("#"):
                    matched = driver.find_elements(By.CSS_SELECTOR, locator)
                else:
                    matched = driver.find_elements(By.XPATH, locator)
                unique_flag = "1 of 1" if len(matched) == 1 else ""
            except Exception:
                unique_flag = ""

            records.append(
                {
                    "tag": el.tag_name,
                    "text": (el.text or "").strip()[:100],
                    "locator": locator,
                    "unique": unique_flag,
                }
            )
            seen.add(locator)

            progress_bar.progress((idx + 1) / total)
            status_text.text(f"Processing element {idx + 1}/{total}")
        except Exception:
            continue

    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(records)

def start_selenium(url):
    if not re.match(r"https?://", url):
        st.error("URL must start with http:// or https://")
        return None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
        )
        driver.get(url)
        time.sleep(3)
        st.info("ℹ️ Please control the browser manually to navigate to different pages.")
        return driver
    except Exception as e:
        st.error(f"Browser start failed: {e}")
        traceback.print_exc()
        return None

def cleanup_driver():
    if "driver" in st.session_state and st.session_state.driver:
        try:
            st.session_state.driver.quit()
        except Exception:
            pass

atexit.register(cleanup_driver)


def clean_excel_file(uploaded_file: io.BytesIO) -> io.BytesIO:
    xls = pd.read_excel(uploaded_file, sheet_name=None)

    # VALIDATION added
    for sheet_name, df in xls.items():
        if sheet_name == "Config":
            continue
        if list(df.columns) != REQUIRED_COLUMNS:
            raise ValueError(
                f"Sheet '{sheet_name}' has invalid columns.\n"
                f"Expected: {REQUIRED_COLUMNS}\n"
                f"Found: {list(df.columns)}"
            )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, df in xls.items():

            df_clean = df.copy()

            if "text" in df_clean.columns:
                df_clean = df_clean[
                    df_clean["text"].notna() &
                    df_clean["text"].astype(str).str.strip().ne("")
                ]

            df_clean.to_excel(
                writer,
                sheet_name=sheet_name[:31] or "Sheet1",
                index=False
            )
    buffer.seek(0)
    return buffer


def run_app():
    st.title("Rule-based Element Extractor")

    if "rule_order" not in st.session_state:
        st.session_state.rule_order = []
    if "assigned_orders" not in st.session_state:
        st.session_state.assigned_orders = {}
    if "driver" not in st.session_state:
        st.session_state.driver = None
    if "captured_data" not in st.session_state:
        st.session_state.captured_data = {}

    st.markdown("#### Please assign priority order to rules for element extraction.")

    available_rules = [
        rule
        for rule in XPATH_RULE_OPTIONS
        if rule not in st.session_state.assigned_orders
    ]

    selected_rule = (
        st.selectbox("Select a rule to assign order", options=available_rules)
        if available_rules
        else None
    )

    if selected_rule:
        max_order = len(XPATH_RULE_OPTIONS)
        used_orders = list(st.session_state.assigned_orders.values())
        available_orders = [i for i in range(1, max_order + 1) if i not in used_orders]

        if available_orders:
            order_num = st.selectbox(
                f"Select priority order", options=available_orders
            )
            if st.button("Submit Rule"):
                if selected_rule in st.session_state.assigned_orders:
                    st.warning(f"Rule '{selected_rule}' is already assigned!")
                elif order_num in used_orders:
                    st.warning(f"Priority {order_num} is already used!")
                else:
                    st.session_state.assigned_orders[selected_rule] = order_num
                    st.session_state.rule_order = [
                        rule
                        for rule, _ in sorted(
                            st.session_state.assigned_orders.items(),
                            key=lambda x: x[1],
                        )
                    ]

    rules_output = ""
    for idx, rule in enumerate(st.session_state.rule_order, 1):
        rules_output += f"{idx}. {rule}\n"
    st.text_area(
        "Selected Rules Priority",
        value=rules_output,
        height=150,
        disabled=True,
    )

    st.markdown("### Application Details")
    app_name = st.text_input("Name", placeholder="MyApp")
    base_url = st.text_input("Base URL", placeholder="https://example.com")

    st.subheader("Element Types To Be Considered in locator extraction.")
    st.caption(
        "Note: For manual addition use one tag per line, prefixed with '-', e.g. '- input', '- button', '- svg', '- tr'."
    )

    elements_text = st.text_area(
        "Element Types",
        value=st.session_state.get("element_types_text", DEFAULT_ELEMENT_TYPES),
        height=210,
        key="element_types_text",
    )

    include_hidden = st.checkbox(
        "Include non-visible elements for deeper search.", value=False
    )

    if st.session_state.driver is None:
        if st.button("🚀 Start Session"):
            driver = start_selenium(base_url)
            if driver:
                st.session_state.driver = driver
                st.success("✅ Browser launched!")

    if st.session_state.driver:
        page_name_start = st.text_input("📄 Enter Page Name for Capture")
        if st.button("➡️ Start Capture"):
            if not page_name_start:
                st.warning("Please enter a Page Name")
            elif not st.session_state.rule_order:
                st.warning("Please assign at least one rule with priority")
            else:
                df = capture_xpaths(
                    st.session_state.driver,
                    st.session_state.rule_order,
                    element_types_text=elements_text,
                    require_displayed=not include_hidden,
                )
                st.session_state.captured_data[page_name_start] = df
                st.success(
                    f"✅ Page captured ({len(df)} elements.)"
                )

    if st.button("🛑 Stop Capture & Download"):
        if st.session_state.driver:
            try:
                st.session_state.driver.quit()
            except Exception:
                pass
        st.session_state.driver = None

        captured = st.session_state.captured_data
        if not captured:
            st.warning("No data captured yet")
        else:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                for page_name, df in captured.items():
                    safe_sheet_name = str(page_name)[:31] or "Sheet1"
                    df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                pd.DataFrame(
                    {
                        "Rule_Priority": [st.session_state.rule_order],
                        "Element_Types": [elements_text],
                    }
                ).to_excel(writer, sheet_name="Config", index=False)

            buffer.seek(0)
            st.download_button(
                label="⬇️ Download Extracted Data",
                data=buffer,
                file_name=f"{app_name or 'extracted'}_{int(time.time())}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.success("✅ Capture session ended.")
            st.session_state.captured_data = {}
            st.session_state.rule_order = []
            st.session_state.assigned_orders = {}

    st.markdown("---")
    st.header("Data Cleaner")

    st.write(
        "Upload extracted Excel file for cleaning"
    )

    st.markdown(
        """
        <div style="background-color:#FF0000;padding:2px;border-radius:8px">
            <span style="font-size:14px;color:white">
            Note: It will remove the entire row for all the sheets if column named as 'TEXT' contains blank row.
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write(
        " "
    )
    uploaded_clean_file = st.file_uploader(
        "Please upload correct extracted file below.",
        type=["xlsx", "xls"],
        key="cleaner_uploader",
    )

    if uploaded_clean_file is not None:
        # Clean and provide download
        try:
            cleaned_buffer = clean_excel_file(uploaded_clean_file)
            st.success("✅ Cleaning complete. Download the cleaned file below.")
            st.download_button(
                label="⬇️ Download Cleaned Excel",
                data=cleaned_buffer,
                file_name="cleaned_extracted_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"Cleaning failed: {e}")


if __name__ == "__main__":
    run_app()
