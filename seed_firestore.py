"""Seed script for FitCoach AI Firestore database."""

from google.cloud import firestore

# Hardcode project ID to avoid issue where GOOGLE_CLOUD_PROJECT returns project number on Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-3a8bb4c7528a"

EXERCISES_SEED = [
    {
        "id": "bench-press",
        "name": "Barbell Bench Press",
        "category": "Chest",
        "target_muscles": ["Pectoralis Major", "Triceps", "Anterior Deltoids"],
        "equipment": "Barbell & Bench",
        "difficulty": "Intermediate",
        "default_sets": 4,
        "default_reps": 8,
        "description": "Lie back on a flat bench. Grip the barbell slightly wider than shoulder-width, lower it to mid-chest, and press up smoothly.",
    },
    {
        "id": "barbell-squat",
        "name": "Barbell Back Squat",
        "category": "Legs",
        "target_muscles": ["Quadriceps", "Glutes", "Hamstrings"],
        "equipment": "Barbell & Squat Rack",
        "difficulty": "Intermediate",
        "default_sets": 4,
        "default_reps": 10,
        "description": "Rest barbell on upper traps. Hinge at hips and knees to lower until thighs are parallel to the floor, then drive up.",
    },
    {
        "id": "deadlift",
        "name": "Conventional Deadlift",
        "category": "Back & Legs",
        "target_muscles": ["Erector Spinae", "Glutes", "Hamstrings", "Lats"],
        "equipment": "Barbell & Weight Plates",
        "difficulty": "Advanced",
        "default_sets": 3,
        "default_reps": 5,
        "description": "Stand over barbell with feet hip-width apart. Hinge hips back, grip bar, keep chest up and back flat, pull bar along shins.",
    },
    {
        "id": "pull-ups",
        "name": "Bodyweight Pull-Ups",
        "category": "Back",
        "target_muscles": ["Latissimus Dorsi", "Biceps", "Rhomboids"],
        "equipment": "Pull-Up Bar",
        "difficulty": "Intermediate",
        "default_sets": 3,
        "default_reps": 8,
        "description": "Grip pull-up bar shoulder-width palms facing away. Pull chest up to the bar, pause, and control the descent.",
    },
    {
        "id": "overhead-press",
        "name": "Standing Overhead Press",
        "category": "Shoulders",
        "target_muscles": ["Deltoids", "Triceps", "Upper Chest"],
        "equipment": "Barbell / Dumbbells",
        "difficulty": "Intermediate",
        "default_sets": 3,
        "default_reps": 8,
        "description": "Stand with feet shoulder-width, hold bar at collarbone, press bar overhead until arms lock out.",
    },
    {
        "id": "plank",
        "name": "Forearm Core Plank",
        "category": "Core",
        "target_muscles": ["Rectus Abdominis", "Obliques", "Transverse Abdominis"],
        "equipment": "Mat / Bodyweight",
        "difficulty": "Beginner",
        "default_sets": 3,
        "default_reps": 60,
        "description": "Place forearms on ground aligned under shoulders. Keep body straight from head to heels and engage core.",
    },
]

INITIAL_WORKOUT_LOG = {
    "workout_name": "Full Body Baseline Session",
    "date": "2026-09-27",
    "duration_minutes": 45,
    "notes": "Great baseline session. Felt strong on squats and bench press.",
    "exercises_completed": [
        {"exercise": "Barbell Back Squat", "sets": 4, "reps": 10, "weight_lbs": 185},
        {"exercise": "Barbell Bench Press", "sets": 4, "reps": 8, "weight_lbs": 155},
        {"exercise": "Bodyweight Pull-Ups", "sets": 3, "reps": 8, "weight_lbs": 0},
    ],
}


def seed_firestore():
    """Seeds exercises and initial workout log into Firestore."""
    db = firestore.Client(project=PROJECT_ID)
    print(f"Connecting to Firestore for project: {PROJECT_ID}")

    # Seed Exercises Collection
    exercises_ref = db.collection("exercises")
    for ex in EXERCISES_SEED:
        doc_id = ex["id"]
        doc_data = {k: v for k, v in ex.items() if k != "id"}
        exercises_ref.document(doc_id).set(doc_data)
        print(f"Seeded exercise: {ex['name']} ({doc_id})")

    # Seed Initial Workout Log
    logs_ref = db.collection("workout_logs")
    logs_ref.add(INITIAL_WORKOUT_LOG)
    print("Seeded baseline workout log.")

    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed_firestore()
