import os
import json
from pathlib import Path
from fastapi import FastAPI, Form, HTTPException
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI()

# LLM Configuration
llm = ChatOpenAI(model="gpt-4o")


# ---TOOL 1: Structure Analyzer---
class StructureAnalyzerTool(BaseTool):
    name: str = "structure_analyzer"
    description: str = "Scans the local directory and returns the folder structure. Use this to understand the project layout."

    def _run(self, base_path: str) -> str:
        try:
            root = Path(base_path)
            if not root.exists(): return "Folder does not exist."
            structure = []
            for path, dirs, files in os.walk(base_path):
                rel_path = os.path.relpath(path, base_path)
                structure.append(f"Folder: {rel_path}")
                for file in files: structure.append(f"  - File: {file}")
            return "\n".join(structure)
        except Exception as e:
            return f"Error: {str(e)}"


# --- TOOL 2: Framework Orchestrator ---
class FrameworkOrchestratorTool(BaseTool):
    name: str = "framework_orchestrator"
    description: str = "Writes generated code files to the local disk based on a JSON map. Input: base_path and files_map_json."

    def _run(self, base_path: str, files_map_json: str) -> str:
        try:
            files_data = json.loads(files_map_json)
            root = Path(base_path)
            for rel_path, content in files_data.items():
                file_path = root / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            return f"✅ Successfully saved files to {base_path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"


# --- ENDPOINTS ---
@app.post("/build-structure")
async def build_structure(
        project_name: str = Form(...),
        language: str = Form(...),
        framework: str = Form(...),
        project_path: str = Form(...)
):
    try:
        base_path = Path(project_path) / project_name
        folders = ["Reports", "Screenshot", "Utils"]
        if language == "Python":
            folders += ["features/steps", "pages"] if framework == "Behave" else ["tests", "pages"]
        elif language == "Java":
            folders += ["src/test/java/stepdefinitions", "src/test/resources/features"]

        for folder in folders:
            (base_path / folder).mkdir(parents=True, exist_ok=True)
        return {"status": "Success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-agent-code")
async def generate_agent_code(
        project_name: str = Form(...),
        language: str = Form(...),
        framework: str = Form(...),
        project_path: str = Form(...),
        bdd_content: str = Form(...)
):
    try:
        base_path = os.path.join(project_path, project_name)

        # Tools instances
        analyzer = StructureAnalyzerTool()
        orchestrator = FrameworkOrchestratorTool()

        sdet_agent = Agent(
            role=f'Senior {language} SDET',
            goal=f'Analyze {base_path} and generate {framework} automation code.',
            backstory=f"Expert in {framework} and Page Object Model. You follow best practices.",
            llm=llm,
            tools=[analyzer, orchestrator],
            verbose=True,
            allow_delegation=False
        )

        task = Task(
            description=f"""
            1. ANALYZE: Use 'structure_analyzer' for {base_path}.
            2. DESIGN: Based on BDD content: '{bdd_content}', write Page Objects and Step/Test files.
            3. SYNC: Save files using 'framework_orchestrator' into the folders found in step 1.
            """,
            expected_output="Code synced to project folders.",
            agent=sdet_agent
        )

        crew = Crew(agents=[sdet_agent], tasks=[task], process=Process.sequential)
        result = crew.kickoff()
        return {"status": "Success", "agent_report": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)