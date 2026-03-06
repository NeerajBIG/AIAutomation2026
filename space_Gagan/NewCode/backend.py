import uuid
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from dotenv import load_dotenv
import json
import subprocess
import sys
import os
from pathlib import Path

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
    tool: str
    language: str
    framework: str
    project_path: str
    bdd_content: str


# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI QA Backend"}


async def get_pytest_expert_prompt(bdd_content):
    prompt = f"""
    You are a Senior Python SDET. Create a professional Pytest-Selenium framework.

    REQUIRED CORE FILES (Mandatory):
    1. 'utils/driver_factory.py': Logic to initialize WebDriver (Chrome/Firefox) with options.
    2. 'pages/base_page.py': A class containing generic methods like click, type, and WebDriverWait.
    3. 'conftest.py': Setup and Teardown fixtures (yield driver) and screenshot on failure.
    4. 'pytest.ini': Configuration for markers and reporting.

    DYNAMIC FILES (Based on BDD):
    - Analyze this BDD: {bdd_content}
    - Create relevant Page Objects in 'pages/' folder.
    - Create relevant Test scripts in 'tests/' folder.

    Output ONLY RAW JSON. No explanations.
    """

    def call_openai_pytest():
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    result = await asyncio.to_thread(call_openai_pytest)

    try:
        files_dict = json.loads(result)
    except json.JSONDecodeError:
        files_dict = {"generated_code.py": result}

    return files_dict

async def get_testng_expert_prompt(bdd_content):
    prompt = f"""
    You are a Java Automation Architect. Create a TestNG Maven framework.

    REQUIRED CORE FILES (Mandatory):
    1. 'src/main/java/utils/DriverManager.java': Singleton or Factory for WebDriver.
    2. 'src/main/java/pages/BasePage.java': Common methods (findElement, waitForElement).
    3. 'src/test/java/tests/BaseTest.java': @BeforeMethod and @AfterMethod for driver setup/quit.
    4. 'pom.xml': All dependencies (Selenium, TestNG, Allure).

    DYNAMIC FILES:
    - Based on BDD: {bdd_content}, generate Page classes in 'src/main/java/pages/' and Test classes in 'src/test/java/tests/'.

    Output ONLY RAW JSON.
    """

    def call_openai_testng():
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    result = await asyncio.to_thread(call_openai_testng)

    try:
        files_dict = json.loads(result)
    except json.JSONDecodeError:
        files_dict = {"generated_code.py": result}

    return files_dict

async def get_behave_expert_prompt(bdd_content):
    prompt = f"""
    You are a Senior BDD Specialist for Python. Create a professional Behave framework.

    REQUIRED CORE FILES (Mandatory):
    1. 'features/environment.py': Implement before_all, after_all, before_scenario hooks for WebDriver initialization and quitting.
    2. 'features/pages/base_page.py': Generic methods class (wait, click, type).
    3. 'behave.ini': Configuration for stdout/stderr capture and reporting.
    4. 'requirements.txt': List all dependencies (behave, selenium, allure-behave, webdriver-manager).

    DYNAMIC FILES (Analyze BDD: {bdd_content}):
    - 'features/*.feature': Create a descriptive feature file based on the BDD.
    - 'features/steps/*.py': Generate step definition logic using the Page Object Model.
    - 'features/pages/*.py': Create dynamic Page Object classes for the entities found in BDD.

    Output ONLY RAW JSON. No explanations. Ensure it is a valid JSON object.
    """

    def call_openai_behave():
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    result = await asyncio.to_thread(call_openai_behave)

    try:
        files_dict = json.loads(result)
    except json.JSONDecodeError:
        files_dict = {"generated_code.py": result}

    return files_dict

async def get_cucumber_expert_prompt(bdd_content):
    prompt = f"""
    You are a Java BDD Architect. Create a professional Cucumber-JUnit framework using Maven.

    REQUIRED CORE FILES (Mandatory):
    1. 'src/test/java/runner/TestRunner.java': JUnit runner class with @CucumberOptions (features, glue, plugins).
    2. 'src/main/java/pages/BasePage.java': Common Selenium wrappers (WebDriverWait, JavascriptExecutor).
    3. 'src/test/java/stepdefinitions/Hooks.java': @Before and @After methods for browser lifecycle management.
    4. 'pom.xml': Maven configuration with Cucumber-Java, Cucumber-JUnit, Selenium, and Allure dependencies.

    DYNAMIC FILES (Analyze BDD: {bdd_content}):
    - 'src/test/resources/features/*.feature': The feature file based on the provided BDD.
    - 'src/test/java/stepdefinitions/*.java': Step definition classes mapping the Gherkin steps to code.
    - 'src/main/java/pages/*.java': Dynamic Page Classes for the UI components mentioned in BDD.

    Output ONLY RAW JSON.
    """

    def call_openai_cucumber():
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    result = await asyncio.to_thread(call_openai_cucumber)

    try:
        files_dict = json.loads(result)
    except json.JSONDecodeError:
        files_dict = {"generated_code.py": result}

    return files_dict


async def get_playwright_ts_expert_prompt(bdd_content):
    prompt = f"""
    You are a Senior Playwright Automation Architect. Create a professional Playwright TypeScript framework.

    REQUIRED CORE FILES (Mandatory):
    1. 'playwright.config.ts': Comprehensive config with projects (Chrome/Firefox/Webkit), reporters (html, allure), and global timeout.
    2. 'package.json': Include scripts for 'test', 'report', and dependencies (@playwright/test, dotenv, allure-playwright).
    3. 'pages/basePage.ts': Base class with common wrappers for Playwright actions (waitForElement, click, fill).
    4. 'pages/pageManager.ts': A central class to initialize all page objects (Page Factory pattern).
    5. 'fixtures/baseTest.ts': Custom fixtures to inject PageManager into tests automatically.
    6. '.env' & '.gitignore': Essential environment and git config files.

    DYNAMIC FILES (Analyze BDD: {bdd_content}):
    - 'tests/*.spec.ts': Create descriptive test cases using the custom fixture.
    - 'pages/*.ts': Create specific Page Object classes for the UI components mentioned.

    Output ONLY RAW JSON. Ensure all file paths are correct for a professional structure.
    """

    def call_openai_playwright():
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    result = await asyncio.to_thread(call_openai_playwright)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"generated_code.ts": result}

async def async_task_generate_code_pytest(task_id: str, bdd_content: str):
    try:
        tasks_store[task_id]["status"] = "processing"
        files_dict = await get_pytest_expert_prompt(bdd_content)
        tasks_store[task_id]["status"] = "done"
        tasks_store[task_id]["result"] = files_dict
    except Exception as e:
        tasks_store[task_id]["status"] = "error"
        tasks_store[task_id]["result"] = str(e)


async def async_task_generate_code_behave(task_id: str, bdd_content: str):
    try:
        tasks_store[task_id]["status"] = "processing"
        files_dict = await get_behave_expert_prompt(bdd_content)
        tasks_store[task_id]["status"] = "done"
        tasks_store[task_id]["result"] = files_dict
    except Exception as e:
        tasks_store[task_id]["status"] = "error"
        tasks_store[task_id]["result"] = str(e)

async def async_task_generate_code_testng(task_id: str, bdd_content: str):
    try:
        tasks_store[task_id]["status"] = "processing"
        files_dict = await get_testng_expert_prompt(bdd_content)
        tasks_store[task_id]["status"] = "done"
        tasks_store[task_id]["result"] = files_dict
    except Exception as e:
        tasks_store[task_id]["status"] = "error"
        tasks_store[task_id]["result"] = str(e)

async def async_task_generate_code_cucumber(task_id: str, bdd_content: str):
    try:
        tasks_store[task_id]["status"] = "processing"
        files_dict = await get_cucumber_expert_prompt(bdd_content)
        tasks_store[task_id]["status"] = "done"
        tasks_store[task_id]["result"] = files_dict
    except Exception as e:
        tasks_store[task_id]["status"] = "error"
        tasks_store[task_id]["result"] = str(e)

async def async_task_generate_code_playwright(task_id: str, bdd_content: str):
    try:
        tasks_store[task_id]["status"] = "processing"
        files_dict = await get_playwright_ts_expert_prompt(bdd_content)
        tasks_store[task_id]["status"] = "done"
        tasks_store[task_id]["result"] = files_dict
    except Exception as e:
        tasks_store[task_id]["status"] = "error"
        tasks_store[task_id]["result"] = str(e)


def dependency_manager(tool: str, language: str, framework: str, project_path: str):
    """
    Automates dependency installation based on Tool -> Language -> Framework hierarchy.
    """
    try:
        t_name = tool.lower()
        lang = language.lower()
        fw = framework.lower()

        # =========================================================
        # CASE 1: SELENIUM TOOL
        # =========================================================
        if "selenium" in t_name:
            if lang == "python":
                # Frameworks: Pytest, Behave
                libs = ["selenium", "webdriver-manager", "requests", "allure-pytest"]
                if fw == "pytest":
                    libs += ["pytest", "pytest-html"]
                elif fw == "behave":
                    libs += ["behave", "allure-behave"]

                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + libs)
                return f"✅ Selenium-Python ({fw}) environment verified."

            elif lang == "java":
                # Frameworks: TestNG, Cucumber (Managed via Maven)
                if os.path.exists(os.path.join(project_path, "pom.xml")):
                    subprocess.check_call(["mvn", "clean", "install"], cwd=project_path, shell=True)
                    return f"✅ Selenium-Java ({fw}) dependencies synced via Maven."
                return "⚠️ pom.xml not found for Java project."

            elif lang == "c#":
                # Frameworks: NUnit, SpecFlow
                libs = ["Selenium.WebDriver", "Selenium.WebDriver.ChromeDriver", "Microsoft.NET.Test.Sdk"]
                if "nunit" in fw:
                    libs += ["NUnit", "NUnit3TestAdapter"]
                elif "specflow" in fw:
                    libs += ["SpecFlow", "SpecFlow.NUnit"]

                for lib in libs:
                    subprocess.check_call(["dotnet", "add", "package", lib], cwd=project_path, shell=True)
                return f"✅ Selenium-C# ({fw}) dependencies installed via Dotnet."

        # =========================================================
        # CASE 2: PLAYWRIGHT TOOL
        # =========================================================
        elif "playwright" in t_name:

            if lang in ["typescript", "javascript"]:
                if os.path.exists(os.path.join(project_path, "package.json")):
                    subprocess.check_call(["npm", "install"], cwd=project_path, shell=True)
                    subprocess.check_call(["npx", "playwright", "install"], cwd=project_path, shell=True)
                    return f"✅ Playwright-{lang} setup complete."
                return "⚠️ package.json missing."

            elif lang == "python":
                libs = ["playwright", "pytest-playwright"]
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + libs)
                subprocess.check_call([sys.executable, "-m", "playwright", "install"])
                return "✅ Playwright-Python setup complete."

            elif lang == "java":
                if os.path.exists(os.path.join(project_path, "pom.xml")):
                    # Maven handles playwright lib, but browsers need manual command or auto-invoke
                    subprocess.check_call(["mvn", "compile"], cwd=project_path, shell=True)
                    # Playwright Java browser install command
                    subprocess.check_call(["mvn", "exec:java", "-e", "-Dexec.mainClass=com.microsoft.playwright.CLI",
                                           "-Dexec.args=install"], cwd=project_path, shell=True)
                    return "✅ Playwright-Java dependencies and browsers installed."
                return "⚠️ pom.xml missing."

            elif lang == "c#":
                subprocess.check_call(["dotnet", "add", "package", "Microsoft.Playwright"], cwd=project_path,
                                      shell=True)
                subprocess.check_call(["dotnet", "build"], cwd=project_path, shell=True)
                subprocess.check_call(["playwright", "install"], cwd=project_path, shell=True)
                return "✅ Playwright-C# setup complete."

        return f"❌ Configuration not supported: {tool} + {language}"

    except Exception as e:
        return f"❌ Dependency Error: {str(e)}"


def framework_orchestrator(action: str, base_path: str, files_map_json: str = "{}"):
    try:
        root = Path(base_path)
        if action == "scan":
            if not root.exists(): return json.dumps({"exists": False})
            files = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
            return json.dumps({"exists": True, "files": files})

        if action == "sync":
            root.mkdir(parents=True, exist_ok=True)
            files_data = json.loads(files_map_json)
            for rel_path, content in files_data.items():
                file_path = root / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            return f"✅ Framework synced at {base_path} with {len(files_data)} artifacts."
    except Exception as e:
        return f"❌ Orchestrator Error: {str(e)}"


# =========================
# API ENDPOINTS
# =========================
@app.post("/generate-agent-code")
async def generate_agent_code(req: GenerateCodeRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks_store[task_id] = {"status": "pending", "result": None}

    fw_lower = req.framework.strip().lower()
    lang_lower = req.language.strip().lower()

    if fw_lower == "pytest" and lang_lower == "python":
        background_tasks.add_task(async_task_generate_code_pytest, task_id, req.bdd_content)
    elif fw_lower == "playwright test" or lang_lower == "typescript":
        background_tasks.add_task(async_task_generate_code_playwright, task_id, req.bdd_content)
    elif fw_lower == "behave":
        background_tasks.add_task(async_task_generate_code_behave, task_id, req.bdd_content)
    elif fw_lower == "testng":
        background_tasks.add_task(async_task_generate_code_testng, task_id, req.bdd_content)
    elif fw_lower == "cucumber":
        background_tasks.add_task(async_task_generate_code_cucumber, task_id, req.bdd_content)

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
