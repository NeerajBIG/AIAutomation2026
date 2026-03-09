import uuid
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from dotenv import load_dotenv
import os
import json

# =========================
# LOAD ENV
# =========================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set!")

openai.api_key = OPENAI_API_KEY

# =========================
# FASTAPI INIT
# =========================
app = FastAPI(title="AI QA Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks_store = {}


# =========================
# Pydantic Models
# =========================
class GenerateCodeRequest(BaseModel):
    project_name: str
    language: str
    framework: str
    project_path: str
    bdd_content: str
    support_content: str = ""


# =========================
# SELENIUM 4 PYTHON STANDARDS
# =========================
SELENIUM_STANDARDS_PYTHON = """
IMPORTANT - Follow Selenium 4 Python standards strictly:

Required imports in every file that uses Selenium:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains  (only if needed)
    from selenium.webdriver.common.keys import Keys  (only if needed)
    from webdriver_manager.chrome import ChromeDriverManager

Use ONLY these locator methods (Selenium 4 standard):
    driver.find_element(By.ID, "value")
    driver.find_element(By.NAME, "value")
    driver.find_element(By.XPATH, "value")
    driver.find_element(By.CSS_SELECTOR, "value")
    driver.find_element(By.CLASS_NAME, "value")
    driver.find_element(By.TAG_NAME, "value")
    driver.find_element(By.LINK_TEXT, "value")
    driver.find_element(By.PARTIAL_LINK_TEXT, "value")
    driver.find_elements(By.XPATH, "value")

Use WebDriverWait for all element interactions:
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "value")))
    WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH, "value")))
    WebDriverWait(browser, 10).until(EC.visibility_of_element_located((By.NAME, "value")))

NEVER use any of these deprecated Selenium 3 methods:
    find_element_by_id()
    find_element_by_name()
    find_element_by_xpath()
    find_element_by_css_selector()
    find_element_by_class_name()
    find_element_by_tag_name()
    find_element_by_link_text()
    find_element_by_partial_link_text()
    find_elements_by_*()
    driver.find_element_by_*()

IMPORTANT - Always generate conftest.py with a 'browser' fixture:
    import pytest
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    @pytest.fixture(scope="session")
    def browser():
        options = Options()
        options.add_argument("--start-maximized")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        yield driver
        driver.quit()

    Rules:
    - Fixture name MUST always be 'browser' (never 'driver')
    - All step definition files must use 'browser' as parameter name
    - conftest.py must be placed at the project root level

IMPORTANT - Always generate a requirements.txt with ALL required packages:
    selenium>=4.0.0
    pytest
    pytest-bdd
    webdriver-manager
    behave
    python-dotenv
"""

# =========================
# SELENIUM 4 JAVA STANDARDS
# =========================
SELENIUM_STANDARDS_JAVA = """
IMPORTANT - Follow Selenium 4 Java standards strictly:

Required imports in every file that uses Selenium:
    import org.openqa.selenium.By;
    import org.openqa.selenium.WebDriver;
    import org.openqa.selenium.WebElement;
    import org.openqa.selenium.support.ui.WebDriverWait;
    import org.openqa.selenium.support.ui.ExpectedConditions;
    import org.openqa.selenium.interactions.Actions;  (only if needed)
    import org.openqa.selenium.Keys;  (only if needed)
    import java.time.Duration;

Use ONLY these locator methods (Selenium 4 standard):
    driver.findElement(By.id("value"))
    driver.findElement(By.name("value"))
    driver.findElement(By.xpath("value"))
    driver.findElement(By.cssSelector("value"))
    driver.findElement(By.className("value"))
    driver.findElement(By.tagName("value"))
    driver.findElement(By.linkText("value"))
    driver.findElement(By.partialLinkText("value"))
    driver.findElements(By.xpath("value"))

Use WebDriverWait with Duration for all element interactions:
    new WebDriverWait(driver, Duration.ofSeconds(10))
        .until(ExpectedConditions.presenceOfElementLocated(By.id("value")));
    new WebDriverWait(driver, Duration.ofSeconds(10))
        .until(ExpectedConditions.elementToBeClickable(By.xpath("value")));
    new WebDriverWait(driver, Duration.ofSeconds(10))
        .until(ExpectedConditions.visibilityOfElementLocated(By.name("value")));

Use @FindBy annotations with PageFactory for Page Object Model:
    @FindBy(id = "username")
    private WebElement usernameField;
    PageFactory.initElements(driver, this);

NEVER use any of these deprecated Selenium 3 methods:
    driver.findElementById()
    driver.findElementByName()
    driver.findElementByXPath()
    driver.findElementByCssSelector()
    driver.findElementByClassName()
    new WebDriverWait(driver, 10)  (without Duration)
"""

# =========================
# PLAYWRIGHT TYPESCRIPT STANDARDS
# =========================
PLAYWRIGHT_STANDARDS_TS = """
IMPORTANT - Follow Playwright TypeScript standards strictly:

Required imports in every file:
    import {{ test, expect }} from '@playwright/test';
    import {{ Page, Locator, Browser, BrowserContext }} from '@playwright/test';  (as needed)

Use ONLY these Playwright locator strategies:
    page.locator('css-or-xpath')
    page.getByRole('button', {{ name: 'Submit' }})
    page.getByLabel('Username')
    page.getByPlaceholder('Enter username')
    page.getByText('Welcome')
    page.getByTestId('login-btn')

Use await for ALL Playwright actions and assertions:
    await page.goto(url);
    await locator.click();
    await locator.fill('value');
    await locator.type('value');
    await expect(locator).toBeVisible();
    await expect(locator).toHaveText('value');
    await expect(locator).toHaveValue('value');
    await expect(page).toHaveURL('url');

Page Object Model pattern:
    export class LoginPage {{
        readonly page: Page;
        readonly usernameInput: Locator;

        constructor(page: Page) {{
            this.page = page;
            this.usernameInput = page.getByLabel('Username');
        }}
    }}

Always generate a package.json with ALL required dependencies:
    {{
        "dependencies": {{
            "@playwright/test": "^1.40.0",
            "typescript": "^5.0.0"
        }},
        "devDependencies": {{
            "@types/node": "^20.0.0"
        }},
        "scripts": {{
            "test": "playwright test",
            "test:headed": "playwright test --headed",
            "test:report": "playwright show-report"
        }}
    }}

NEVER use:
    Selenium-style locators or methods
    document.querySelector() or other DOM methods
    Non-async calls to Playwright methods
"""

# =========================
# LOCATOR USAGE STANDARDS
# =========================
LOCATOR_USAGE_STANDARDS = """
CRITICAL - Element Locators Usage:

The Supporting Information section contains element locators in this format:
    ElementName (Type: LOCATOR_TYPE): locator_value

You MUST use these EXACT locators in the generated code. DO NOT generate your own locators.

Locator Type mapping:
    XPATH       → By.XPATH, "locator_value"
    ID          → By.ID, "locator_value"
    NAME        → By.NAME, "locator_value"
    CSS         → By.CSS_SELECTOR, "locator_value"
    CLASS_NAME  → By.CLASS_NAME, "locator_value"
    LINK_TEXT   → By.LINK_TEXT, "locator_value"

Example - if Supporting Information contains:
    UsernameField (Type: XPATH): //input[@id='un']
    PasswordField (Type: XPATH): //input[@id='pw']
    SubmitButton  (Type: XPATH): //input[@id='jsLoginButton']

Then generated code MUST use:
    username_field = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@id='un']"))
    )
    password_field = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@id='pw']"))
    )
    submit_button = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@id='jsLoginButton']"))
    )

NEVER substitute, modify or guess locators.
NEVER use By.ID, By.NAME or any other type unless it exactly matches the Type in Supporting Information.
If a locator is provided in Supporting Information, use it exactly as given — no exceptions.
"""


# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI QA Backend"}


# =========================
# HELPER: Call OpenAI
# =========================
async def call_openai(prompt: str) -> str:
    def _call():
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content
    return await asyncio.to_thread(_call)


def parse_json_result(result: str, fallback_key: str) -> dict:
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        clean = result.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            return {fallback_key: result}


# =========================
# Python - Pytest
# =========================
async def generate_python_pytest(bdd_content: str, support_content: str) -> dict:
    prompt = f"""
    You are an expert QA automation engineer specialized in Python Pytest framework with Selenium WebDriver.

    Based on the following BDD content, generate a complete Pytest test structure.
    Use the supporting information provided (base URL, credentials, element locators) in the generated code.

    Return the results as a JSON object containing ALL of these files:
    - conftest.py              (root level - browser fixture using webdriver_manager)
    - tests/test_*.py          (test cases using pytest-bdd)
    - features/*.feature       (BDD feature files)
    - steps/*_steps.py         (step definitions)
    - requirements.txt         (all required packages)

    Do not include explanations, only valid code files as JSON.

    Example JSON response:
    {{
        "conftest.py": "...",
        "tests/test_login.py": "...",
        "features/login.feature": "...",
        "steps/login_steps.py": "...",
        "requirements.txt": "..."
    }}

    {SELENIUM_STANDARDS_PYTHON}

    {LOCATOR_USAGE_STANDARDS}

    Supporting Information:
    {support_content}

    BDD Content:
    {bdd_content}
    """
    result = await call_openai(prompt)
    return parse_json_result(result, "tests/generated_test.py")


# =========================
# Python - Behave
# =========================
async def generate_python_behave(bdd_content: str, support_content: str) -> dict:
    prompt = f"""
    You are an expert QA automation engineer specialized in Python Behave framework with Selenium WebDriver.

    Based on the following BDD content, generate a complete Behave test structure.
    Use the supporting information provided (base URL, credentials, element locators) in the generated code.

    Return the results as a JSON object containing ALL of these files:
    - features/*.feature           (BDD feature files)
    - features/steps/*_steps.py    (step definitions)
    - environment.py               (hooks: before_all, after_all, before_scenario, after_scenario)
    - requirements.txt             (all required packages)

    Do not include explanations, only valid code files as JSON.

    Example JSON response:
    {{
        "features/login.feature": "...",
        "features/steps/login_steps.py": "...",
        "environment.py": "...",
        "requirements.txt": "..."
    }}

    {SELENIUM_STANDARDS_PYTHON}

    {LOCATOR_USAGE_STANDARDS}

    Supporting Information:
    {support_content}

    BDD Content:
    {bdd_content}
    """
    result = await call_openai(prompt)
    return parse_json_result(result, "features/generated.feature")


# =========================
# Java - TestNG
# =========================
async def generate_java_testng(bdd_content: str, support_content: str) -> dict:
    prompt = f"""
    You are an expert QA automation engineer specialized in Java TestNG framework with Selenium WebDriver.

    Based on the following BDD content, generate a complete TestNG test structure.
    Use the supporting information provided (base URL, credentials, element locators) in the generated code.

    Return the results as a JSON object containing ALL of these files:
    - src/test/java/tests/*.java          (TestNG test classes)
    - src/test/java/pages/*.java          (Page Object Model classes)
    - src/test/java/utils/BaseTest.java   (base test setup/teardown)
    - src/test/resources/testng.xml       (TestNG suite configuration)
    - pom.xml                             (Maven dependencies - Selenium 4, TestNG, WebDriverManager)

    Do not include explanations, only valid code files as JSON.

    Example JSON response:
    {{
        "src/test/java/tests/LoginTest.java": "...",
        "src/test/java/pages/LoginPage.java": "...",
        "src/test/java/utils/BaseTest.java": "...",
        "src/test/resources/testng.xml": "...",
        "pom.xml": "..."
    }}

    {SELENIUM_STANDARDS_JAVA}

    {LOCATOR_USAGE_STANDARDS}

    Supporting Information:
    {support_content}

    BDD Content:
    {bdd_content}
    """
    result = await call_openai(prompt)
    return parse_json_result(result, "src/test/java/tests/GeneratedTest.java")


# =========================
# Java - Cucumber
# =========================
async def generate_java_cucumber(bdd_content: str, support_content: str) -> dict:
    prompt = f"""
    You are an expert QA automation engineer specialized in Java Cucumber framework with Selenium WebDriver.

    Based on the following BDD content, generate a complete Cucumber-JVM test structure.
    Use the supporting information provided (base URL, credentials, element locators) in the generated code.

    Return the results as a JSON object containing ALL of these files:
    - src/test/resources/features/*.feature    (BDD feature files)
    - src/test/java/steps/*Steps.java          (step definitions)
    - src/test/java/pages/*.java               (Page Object Model classes)
    - src/test/java/hooks/Hooks.java           (before/after hooks)
    - src/test/java/runner/TestRunner.java     (Cucumber runner)
    - pom.xml                                  (Maven dependencies - Selenium 4, Cucumber, WebDriverManager)

    Do not include explanations, only valid code files as JSON.

    Example JSON response:
    {{
        "src/test/resources/features/login.feature": "...",
        "src/test/java/steps/LoginSteps.java": "...",
        "src/test/java/pages/LoginPage.java": "...",
        "src/test/java/hooks/Hooks.java": "...",
        "src/test/java/runner/TestRunner.java": "...",
        "pom.xml": "..."
    }}

    {SELENIUM_STANDARDS_JAVA}

    {LOCATOR_USAGE_STANDARDS}

    Supporting Information:
    {support_content}

    BDD Content:
    {bdd_content}
    """
    result = await call_openai(prompt)
    return parse_json_result(result, "src/test/resources/features/generated.feature")


# =========================
# Playwright - TypeScript
# =========================
async def generate_playwright_typescript(bdd_content: str, support_content: str) -> dict:
    prompt = f"""
    You are an expert QA automation engineer specialized in Playwright with TypeScript.

    Based on the following BDD content, generate a complete Playwright TypeScript test structure.
    Use the supporting information provided (base URL, credentials, element locators) in the generated code.

    Return the results as a JSON object containing ALL of these files:
    - tests/*.spec.ts          (Playwright test files)
    - pages/*.ts               (Page Object Model classes)
    - fixtures/base.ts         (custom fixtures and setup)
    - playwright.config.ts     (Playwright configuration)
    - package.json             (all required dependencies)

    Do not include explanations, only valid code files as JSON.

    Example JSON response:
    {{
        "tests/login.spec.ts": "...",
        "pages/LoginPage.ts": "...",
        "fixtures/base.ts": "...",
        "playwright.config.ts": "...",
        "package.json": "..."
    }}

    {PLAYWRIGHT_STANDARDS_TS}

    {LOCATOR_USAGE_STANDARDS}

    Supporting Information:
    {support_content}

    BDD Content:
    {bdd_content}
    """
    result = await call_openai(prompt)
    return parse_json_result(result, "tests/generated.spec.ts")


# =========================
# ROUTER: Pick correct generator
# =========================
async def route_code_generation(language: str, framework: str, bdd_content: str, support_content: str) -> dict:
    key = (language.strip().lower(), framework.strip().lower())

    routes = {
        ("python", "pytest"):           generate_python_pytest,
        ("python", "behave"):           generate_python_behave,
        ("java", "testng"):             generate_java_testng,
        ("java", "cucumber"):           generate_java_cucumber,
        ("playwright", "typescript"):   generate_playwright_typescript,
    }

    generator = routes.get(key)
    if not generator:
        raise ValueError(f"Unsupported combination: {language} - {framework}")

    return await generator(bdd_content, support_content)


# =========================
# TASK HELPER
# =========================
async def async_task_generate_code(
    task_id: str,
    language: str,
    framework: str,
    bdd_content: str,
    support_content: str
):
    try:
        tasks_store[task_id]["status"] = "processing"
        files_dict = await route_code_generation(language, framework, bdd_content, support_content)
        tasks_store[task_id]["status"] = "done"
        tasks_store[task_id]["result"] = files_dict
    except Exception as e:
        tasks_store[task_id]["status"] = "error"
        tasks_store[task_id]["result"] = str(e)


# =========================
# API ENDPOINTS
# =========================
@app.post("/generate-agent-code")
async def generate_agent_code(req: GenerateCodeRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks_store[task_id] = {"status": "pending", "result": None}

    background_tasks.add_task(
        async_task_generate_code,
        task_id,
        req.language,
        req.framework,
        req.bdd_content,
        req.support_content
    )

    return {"task_id": task_id, "message": "Task started."}


@app.get("/task-result/{task_id}")
async def get_task_result(task_id: str):
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task ID not found")
    return tasks_store[task_id]


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)