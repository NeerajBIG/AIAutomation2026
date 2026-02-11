import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import io
from openai import OpenAI
import os
import traceback
from dotenv import load_dotenv
import atexit
import re

# ============================================================
# Default XPath Rules
# ============================================================
DEFAULT_XPATH_RULES = """# XPath Generation Rules
1. Text-based XPath (HIGHEST PRIORITY)
2. ID-based XPath
3. Name attribute
4. Unique attributes
"""

# Element Types
DEFAULT_ELEMENT_TYPES = """- input
- button
- a
- select
- textarea
- span
- div
"""

# ============================================================
# OpenAI Wrapper
# ============================================================
class OpenAIWrapper:
    def __init__(self, xpath_rules=None):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY_NEW")
        if not self.api_key:
            st.error("OpenAI API key not found.")
            st.stop()
        self.client = OpenAI(api_key=self.api_key)
        self.xpath_rules = xpath_rules or DEFAULT_XPATH_RULES

    def generate_xpath(self, element_outer_html: str, element_text: str, element_id: str, element_name: str,
                       element_tag: str):
        prompt = f"""You are an XPath expert. Follow the rules strictly.

{self.xpath_rules}

Generate XPath for:
- Tag: {element_tag}
- Text: {element_text[:100] if element_text else "none"}
- ID: {element_id or "none"}
- Name: {element_name or "none"}
- HTML: {element_outer_html[:300]}

Return ONLY the XPath string.
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "Return ONLY the XPath string."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=100
            )
            xpath = response.choices[0].message.content.strip()
            xpath = xpath.replace('```', '').replace('xpath', '').strip()
            return xpath
        except Exception as e:
            st.error(f"OpenAI error: {e}")
            return None

# ============================================================
# Build XPath
# ============================================================
def build_preferred_xpath(driver, element, ai_client, use_ai=True):
    try:
        element_outer_html = element.get_attribute("outerHTML")
        element_text = element.text.strip()
        element_id = element.get_attribute("id") or ""
        element_name = element.get_attribute("name") or ""
        element_tag = element.tag_name
    except:
        element_outer_html = element_text = element_id = element_name = element_tag = ""

    if use_ai and ai_client:
        ai_xpath = ai_client.generate_xpath(element_outer_html, element_text, element_id, element_name, element_tag)
        if ai_xpath and ai_xpath.startswith('//'):
            return ai_xpath

    if element_text and len(element_text) < 50:
        clean_text = element_text.replace("'", "\\'")
        return f"//{element_tag}[text()='{clean_text}']"
    if element_id:
        return f"//{element_tag}[@id='{element_id}']"
    if element_name:
        return f"//{element_tag}[@name='{element_name}']"
    try:
        element_type = element.get_attribute("type")
        if element_type and element_tag in ['input', 'button']:
            return f"//{element_tag}[@type='{element_type}']"
    except:
        pass
    return f"//{element_tag}  [⚠️ NOT UNIQUE]"

# ============================================================
# Capture DOM + XPaths
# ============================================================
def parse_element_types(element_types_text):
    elements = []
    for line in element_types_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('-'):
            line = line[1:].strip()
            if '(' in line:
                element = line.split('(')[0].strip()
            else:
                element = line
            if element and ' ' not in element and len(element) < 20:
                elements.append(element.lower())
    if not elements:
        return ['button', 'a', 'input', 'select', 'textarea', 'span', 'div']
    return elements

def build_xpath_query(element_types):
    valid_elements = [e for e in element_types if e.isalnum() and len(e) < 20]
    if not valid_elements:
        valid_elements = ['button', 'a', 'input', 'select', 'textarea', 'span', 'div']
    conditions = [f"self::{elem}" for elem in valid_elements]
    return f"//*[{ ' or '.join(conditions) }]"

def capture_xpaths(driver, ai_client, use_ai=True, element_types_text=None):
    element_types = parse_element_types(element_types_text or DEFAULT_ELEMENT_TYPES)
    xpath_query = build_xpath_query(element_types)
    st.info(f"🎯 Targeting elements: {', '.join(element_types)}")
    try:
        elements = driver.find_elements(By.XPATH, xpath_query)
    except Exception as e:
        st.error(f"XPath query failed: {e}")
        return pd.DataFrame()

    if len(elements) == 0:
        st.warning("No elements found.")
        return pd.DataFrame()

    records = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    current_page_xpaths = set()

    for idx, el in enumerate(elements):
        try:
            if not el.is_displayed():
                continue
            xpath = build_preferred_xpath(driver, el, ai_client, use_ai)
            if xpath.endswith("[⚠️ NOT UNIQUE]") or xpath in st.session_state.captured_xpaths:
                continue
            tag = el.tag_name
            text = el.text.strip()[:100]
            records.append({"tag": tag, "text": text, "xpath": xpath})
            current_page_xpaths.add(xpath)
            progress_bar.progress((idx + 1) / len(elements))
            status_text.text(f"Processing element {idx + 1}/{len(elements)}")
        except:
            continue

    progress_bar.empty()
    status_text.empty()
    df = pd.DataFrame(records)
    st.session_state.captured_xpaths.update(current_page_xpaths)
    return df

# ============================================================
# Start Selenium Browser
# ============================================================
def start_selenium(url):
    if not re.match(r'https?://', url):
        st.error("URL must start with http:// or https://")
        return None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        time.sleep(3)
        st.info("ℹ️ Please login manually in the opened browser if required.")
        return driver
    except Exception as e:
        st.error(f"Browser start failed: {e}")
        traceback.print_exc()
        return None

# ============================================================
# Utilities
# ============================================================
def generate_unique_sheet_name(base_name, existing_names):
    max_length = 31
    if len(base_name) > max_length - 3:
        base_name = base_name[:max_length - 3]
    if base_name not in existing_names:
        return base_name
    counter = 1
    while True:
        new_name = f"{base_name}_{counter}"
        if len(new_name) > max_length:
            truncate_length = max_length - len(f"_{counter}")
            new_name = f"{base_name[:truncate_length]}_{counter}"
        if new_name not in existing_names:
            return new_name
        counter += 1

def cleanup_driver():
    if "driver" in st.session_state and st.session_state.driver:
        try:
            st.session_state.driver.quit()
        except:
            pass
atexit.register(cleanup_driver)

# ============================================================
# Main Streamlit App
# ============================================================
def run_app():
    st.title("Rule-based Element Extractor - Powered by AI")

    app_name = st.text_input("Application Name", placeholder="MyApp")
    base_url = st.text_input("Base URL", placeholder="https://example.com")

    #use_ai = st.checkbox("Use AI for XPath Generation", value=False)
    use_ai = False
    rules_text = st.text_area("Element Locators Rules", value=DEFAULT_XPATH_RULES, height=170, disabled=True)
    elements_text = st.text_area("Element Types To Be Considered", value=DEFAULT_ELEMENT_TYPES, height=210, disabled=True)

    if "driver" not in st.session_state:
        st.session_state.driver = None
    if "ai_client" not in st.session_state:
        st.session_state.ai_client = None
    if "captured_data" not in st.session_state:
        st.session_state.captured_data = {}
    if "captured_xpaths" not in st.session_state:
        st.session_state.captured_xpaths = set()
    if "page_name_input" not in st.session_state:
        st.session_state.page_name_input = ""

    # ------------------- Start Session -------------------
    if st.session_state.driver is None:
        if st.button("🚀 Start Session"):
            driver = start_selenium(base_url)
            if driver:
                st.session_state.driver = driver
                st.success("✅ Browser launched! Now you can Start Capture.")

    # ------------------- Start Capture -------------------
    if st.session_state.driver:
        page_name_start = st.text_input("📄 Page Name for Capture")
        if st.button("➡️ Start Capture"):
            if not page_name_start:
                st.warning("Please enter a Page Name")
            else:
                if use_ai:
                    st.session_state.ai_client = OpenAIWrapper(xpath_rules=rules_text)
                df = capture_xpaths(st.session_state.driver, st.session_state.ai_client, use_ai=use_ai,
                                    element_types_text=elements_text)
                page_name = generate_unique_sheet_name(page_name_start, list(st.session_state.captured_data.keys()))
                st.session_state.captured_data[page_name] = df
                st.success(f"✅ Page captured: {page_name} ({len(df)} elements)")

    # ------------------- Stop Capture -------------------
    if st.button("🛑 Stop Capture & Download"):
        if not st.session_state.driver:
            st.warning("⚠️ No active session.")
            return

        # Close browser
        try:
            st.session_state.driver.quit()
            st.success("Browser closed")
        except Exception as e:
            st.warning(f"Could not close browser: {e}")

        st.session_state.driver = None

        # Build Excel
        captured = st.session_state.captured_data
        if not captured:
            st.warning("No data captured yet")
            return

        with st.spinner("Building Excel file..."):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                for page_name, df in captured.items():
                    df.to_excel(writer, sheet_name=page_name, index=False)
                pd.DataFrame({"element_types": [elements_text]}).to_excel(
                    writer, sheet_name="Config_Elements", index=False
                )
            buffer.seek(0)

            st.download_button(
                label="⬇️ Download Extracted Data",
                data=buffer,
                file_name=f"{app_name or 'extracted'}_{int(time.time())}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.success("✅ Capture session ended. Data ready for download.")
        st.session_state.captured_data = {}
        st.session_state.captured_xpaths = set()
        st.session_state.page_name_input = ""

# ============================================================
# Run if main
# ============================================================
if __name__ == "__main__":
    run_app()
