"""Firestore function tools for FitCoach AI."""

import datetime
from google.adk.tools import ToolContext
from google.cloud import firestore

# Hardcode project ID to avoid issue where GOOGLE_CLOUD_PROJECT returns project number on Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-3a8bb4c7528a"


def _get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def list_exercises(category: str = None) -> list[dict]:
    """Lists available exercises from the FitCoach catalog.

    Args:
        category: Optional filter by muscle group / category (e.g. 'Chest', 'Legs', 'Back', 'Core', 'Shoulders').

    Returns:
        List of exercise dictionaries matching the query.
    """
    db = _get_firestore_client()
    query_ref = db.collection("exercises")

    if category:
        query_ref = query_ref.where("category", "==", category.title())

    docs = query_ref.stream()
    results = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        results.append(item)

    if not results and category:
        # Fallback to fetching all and doing case-insensitive match
        all_docs = db.collection("exercises").stream()
        for doc in all_docs:
            item = doc.to_dict()
            item["id"] = doc.id
            if item.get("category", "").lower() == category.lower():
                results.append(item)

    return results


def get_exercise_details(exercise_name_or_id: str) -> dict:
    """Retrieves full details for a specific exercise by name or ID.

    Args:
        exercise_name_or_id: The document ID (e.g., 'bench-press') or exercise name (e.g. 'Barbell Bench Press').

    Returns:
        Dictionary containing exercise details, or error message if not found.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("exercises").document(exercise_name_or_id.lower().replace(" ", "-"))
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    # Search by name field
    docs = db.collection("exercises").stream()
    for d in docs:
        item = d.to_dict()
        if exercise_name_or_id.lower() in item.get("name", "").lower() or d.id == exercise_name_or_id.lower():
            item["id"] = d.id
            return item

    return {"error": f"Exercise '{exercise_name_or_id}' not found in catalog."}


def log_workout_session(
    workout_name: str,
    exercises_completed: list[dict],
    duration_minutes: int = 45,
    notes: str = "",
) -> dict:
    """Logs a completed workout session into the user's workout history in Firestore.

    Args:
        workout_name: Name or description of the workout (e.g. 'Push Day', 'Leg Day Routine').
        exercises_completed: List of dicts, each with 'exercise', 'sets', 'reps', and 'weight_lbs' (or 'weight').
        duration_minutes: Duration of the session in minutes.
        notes: Any notes on form, feeling, or progression.

    Returns:
        Confirmation dictionary with saved document ID and status.
    """
    db = _get_firestore_client()
    today_str = datetime.date.today().isoformat()

    log_entry = {
        "workout_name": workout_name,
        "date": today_str,
        "duration_minutes": duration_minutes,
        "notes": notes,
        "exercises_completed": exercises_completed,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    doc_ref = db.collection("workout_logs").add(log_entry)
    doc_id = doc_ref[1].id

    hours = round(duration_minutes / 60.0, 2)
    return {
        "status": "success",
        "message": f"Successfully logged workout '{workout_name}' on date {today_str} for {duration_minutes} minutes ({hours} hours exercised).",
        "document_id": doc_id,
        "logged_data": log_entry,
        "date": today_str,
        "hours_exercised": hours,
    }


def get_workout_logs(limit: int = 5) -> list[dict]:
    """Retrieves recent workout session logs from the user's workout history.

    Args:
        limit: Maximum number of recent workout logs to return (default 5).

    Returns:
        List of recent workout log dictionaries.
    """
    db = _get_firestore_client()
    docs = db.collection("workout_logs").stream()

    logs = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        logs.append(data)

    # Sort by date / timestamp descending if present
    logs.sort(key=lambda x: x.get("date", x.get("timestamp", "")), reverse=True)
    return logs[:limit]


def calculate_fitness_metrics(
    weight_lbs: float,
    reps: int,
    sets: int = 1,
    body_weight_lbs: float = 170.0,
) -> dict:
    """Calculates fitness metrics including estimated 1RM (One-Rep Max) and total workout volume.

    Args:
        weight_lbs: Weight lifted in pounds (use 0 for bodyweight exercises).
        reps: Number of repetitions completed per set.
        sets: Number of sets completed (default 1).
        body_weight_lbs: User's body weight in pounds (default 170.0, used for bodyweight 1RM estimation).

    Returns:
        Dictionary containing estimated 1RM, total volume lifted, and calculation summary.
    """
    effective_weight = weight_lbs if weight_lbs > 0 else (body_weight_lbs * 0.65)

    # Epley formula: 1RM = weight * (1 + reps / 30)
    if reps == 1:
        one_rep_max = effective_weight
    else:
        one_rep_max = round(effective_weight * (1 + reps / 30.0), 1)

    total_volume = round(effective_weight * reps * sets, 1)

    return {
        "weight_lbs": weight_lbs,
        "reps": reps,
        "sets": sets,
        "estimated_1rm_lbs": one_rep_max,
        "total_volume_lbs": total_volume,
        "formula": "Epley Formula: 1RM = weight * (1 + reps / 30)",
    }


def fetch_public_exercise_info(search_term: str = "") -> list[dict]:
    """Fetches real exercise data from the open-source wger Workout Manager public API.

    Args:
        search_term: Optional keyword to filter exercises (e.g. 'Press', 'Squat', 'Ab', 'Kettlebell').

    Returns:
        List of matching exercise info dictionaries from the wger public API.
    """
    import json
    import os
    import urllib.request

    api_key = os.environ.get("WGER_API_KEY", "")
    url = "https://wger.de/api/v2/exerciseinfo/?limit=30"
    headers = {"User-Agent": "FitCoachAI/1.0"}
    if api_key:
        headers["Authorization"] = f"Token {api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in data.get("results", []):
            english_trans = [t for t in item.get("translations", []) if t.get("language") == 2]
            name = english_trans[0]["name"] if english_trans else (item.get("name") or "Exercise")
            desc = english_trans[0]["description_source"] if english_trans else ""
            category = item.get("category", {}).get("name", "General")

            if not search_term or search_term.lower() in name.lower() or search_term.lower() in category.lower():
                results.append({
                    "name": name,
                    "category": category,
                    "equipment": [e.get("name") for e in item.get("equipment", [])],
                    "muscles": [m.get("name") for m in item.get("muscles", [])],
                    "description": desc[:150] + "..." if len(desc) > 150 else desc,
                })

        return results[:5] if results else [{"message": f"No public exercises found matching '{search_term}'."}]
    except Exception as e:
        return [{"error": f"Failed to fetch from wger public API: {str(e)}"}]


async def generate_workout_image(
    prompt: str,
    tool_context: ToolContext,
) -> dict:
    """Generates an image for a workout, exercise form visual, or milestone badge using Gemini Flash Lite Image.

    Args:
        prompt: Detailed description of the image to generate (e.g., 'A modern minimalist workout badge for 100kg bench press').
        tool_context: ADK ToolContext injected automatically.

    Returns:
        Dictionary containing the public Cloud Storage URL of the generated image and status.
    """
    import time
    from google import genai
    from google.cloud import storage
    from google.genai import types

    BUCKET_NAME = "fitcoach-ai-assets-qwiklabs-gcp-03-3a8bb4c7528a"

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    image_bytes = None
    mime_type = "image/png"
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/png"
                break

    if not image_bytes:
        return {"error": "Failed to generate image bytes from Gemini model."}

    ext = "png" if "png" in mime_type else "jpg"
    filename = f"workout_image_{int(time.time())}.{ext}"

    # 1. Save artifact so it shows up in Playground's Artifacts panel
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image bytes directly to public GCS bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "image_url": public_url,
        "filename": filename,
        "message": f"Successfully generated image and uploaded to public GCS bucket.",
    }


async def generate_workout_video(
    prompt: str,
    tool_context: ToolContext,
) -> dict:
    """Generates a short exercise visual guide video using Google's Omni model (gemini-omni-flash-preview).

    Args:
        prompt: Detailed description of the exercise demonstration video to generate (e.g., 'A 5-second video demonstrating a push-up with proper form').
        tool_context: ADK ToolContext injected automatically.

    Returns:
        Dictionary containing the public Cloud Storage URL of the generated video and status.
    """
    import base64
    import time
    from google import genai
    from google.cloud import storage
    from google.genai import types

    BUCKET_NAME = "fitcoach-ai-assets-qwiklabs-gcp-03-3a8bb4c7528a"

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt,
    )

    video_bytes = None
    mime_type = "video/mp4"

    if hasattr(interaction, "output_video") and interaction.output_video:
        data = getattr(interaction.output_video, "data", None) or getattr(interaction.output_video, "bytes", None)
        if data:
            video_bytes = base64.b64decode(data) if isinstance(data, str) else data
            mime_type = getattr(interaction.output_video, "mime_type", "video/mp4") or "video/mp4"

    if not video_bytes and hasattr(interaction, "steps") and interaction.steps:
        for step in interaction.steps:
            if hasattr(step, "outputs") and step.outputs:
                for out in step.outputs:
                    data = getattr(out, "data", None) or getattr(out, "bytes", None)
                    if data:
                        video_bytes = base64.b64decode(data) if isinstance(data, str) else data
                        mime_type = getattr(out, "mime_type", "video/mp4") or "video/mp4"
                        break

    if not video_bytes:
        return {"error": "Failed to generate video bytes from gemini-omni-flash-preview model."}

    ext = "mp4" if "mp4" in mime_type else "webm"
    filename = f"workout_video_{int(time.time())}.{ext}"

    # 1. Save artifact so it shows up in Playground's Artifacts panel
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload video bytes directly to public GCS bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "video_url": public_url,
        "filename": filename,
        "message": "Successfully generated video and uploaded to public GCS bucket.",
    }




