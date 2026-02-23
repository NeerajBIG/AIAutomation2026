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


# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI QA Backend"}

# =========================
# AI CODE GENERATION (Generic)
# =========================
async def generate_code_ai(bdd_content: str, language: str, framework: str) -> dict:
    prompt = f"""
    You are an expert QA automation engineer.

    Based on the following BDD content, generate automation code in {language} using {framework}.
    Return separate files as a JSON object:
    - conftest.py (or equivalent)
    - test_*.py files
    - step definition files (if applicable)
    - feature files (if applicable)
    - runner file (if applicable)

    Example JSON response:
    {{
        "conftest.py": "...",
        "test_login.py": "...",
        "features/login.feature": "...",
        "steps/login_steps.py": "...",
        "runner.py": "..."
    }}

    BDD Content:
    {bdd_content}
    """

    def call_openai():
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    result = await asyncio.to_thread(call_openai)

    try:
        files_dict = json.loads(result)
    except json.JSONDecodeError:
        files_dict = {"generated_code.py": result}

    return files_dict


# =========================
# AI CODE GENERATION (Behave Only)
# =========================
async def generate_code_behave_ai(bdd_content: str) -> dict:
    prompt = f"""
    You are an expert QA automation engineer specialized in Python Behave framework.

    Based on the following BDD content, generate a complete Behave test structure.
    Return the results as a JSON object containing:
    - feature files under 'features/' directory
    - step definition files under 'features/steps/'
    - environment.py (if required)
    - any necessary configuration or runner files

    Ensure all syntax and structure follow standard Behave conventions.
    Do not include explanations, only valid code files as JSON.

    Example JSON response:
    {{
        "features/login.feature": "...",
        "features/steps/login_steps.py": "...",
        "environment.py": "..."
    }}

    BDD Content:
    {bdd_content}
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
        files_dict = {"features/generated.feature": result}

    return files_dict


# =========================
# TASK HELPERS
# =========================
async def async_task_generate_code(task_id: str, bdd_content: str, language: str, framework: str):
    try:
        tasks_store[task_id]["status"] = "processing"
        files_dict = await generate_code_ai(bdd_content, language, framework)
        tasks_store[task_id]["status"] = "done"
        tasks_store[task_id]["result"] = files_dict
    except Exception as e:
        tasks_store[task_id]["status"] = "error"
        tasks_store[task_id]["result"] = str(e)


async def async_task_generate_behave(task_id: str, bdd_content: str):
    try:
        tasks_store[task_id]["status"] = "processing"
        files_dict = await generate_code_behave_ai(bdd_content)
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

    # Special handling for Behave
    if req.framework.strip().lower() == "behave" and req.language.strip().lower() == "python":
        background_tasks.add_task(async_task_generate_behave, task_id, req.bdd_content)
    else:
        background_tasks.add_task(async_task_generate_code, task_id, req.bdd_content, req.language, req.framework)

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
