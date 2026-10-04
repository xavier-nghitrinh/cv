import os
from google import genai
from google.cloud import firestore
from google.cloud import storage

PROJECT_ID = os.environ.get("GCP_PROJECT", "nm-prod-454707")
LOCATION = os.environ.get("GCP_LOCATION", "global")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET", "job-app")
FIRESTORE_DATABASE = os.environ.get("FIRESTORE_DATABASE", "job-app")
FIRESTORE_COLLECTION = "applications"
PROFILE_DOC_ID = "user_profile"

# Global singleton client instances
_firestore_client = None
_storage_client = None
_genai_client = None

def get_firestore_client():
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DATABASE)
    return _firestore_client

def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client

def get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    return _genai_client

MODEL_NAME = "gemini-3.7-flash"
