# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
from app.tools import (
    calculate_fitness_metrics,
    fetch_public_exercise_info,
    generate_workout_image,
    generate_workout_video,
    get_exercise_details,
    get_workout_logs,
    list_exercises,
    log_workout_session,
)

# Load remote_agent_runtime_id from deployment_metadata.json if present
agent_engine_resource_name = None
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
if metadata_path.exists():
    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
    except Exception:
        pass


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "FitCoach AI, an expert encouraging personal workout coach and fitness assistant. "
        "You help users explore exercises from the local catalog and public wger database, design workout plans, "
        "log completed workout sessions into Firestore, review workout logs, calculate 1RM / workout volume metrics, "
        "generate custom workout badge images, and run Python code in a safe sandbox for data analysis. "
        "You remember user preferences, facts, and ALL workout activity across conversations. "
        "Specifically, always track, state, and remember the exact dates and total hours/minutes exercised whenever the user completes, logs, or mentions a workout session."
    ),
    workflow_description="Analyze the user request, call necessary tools or code execution, and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=agent_engine_resource_name,
    ),
    tools=[
        PreloadMemoryTool(),
        list_exercises,
        get_exercise_details,
        log_workout_session,
        get_workout_logs,
        calculate_fitness_metrics,
        fetch_public_exercise_info,
        generate_workout_image,
        generate_workout_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
