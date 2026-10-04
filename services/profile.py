import os
from google.cloud import storage
from services.gcp import get_firestore_client, get_genai_client, GCS_BUCKET_NAME, PROFILE_DOC_ID

DEFAULT_PROFILE = """Xavier Trinh
AI-Driven Data & Analytics Leader
Contact: xavier.nghitrinh@gmail.com | (+61) 468 664 940
LinkedIn: https://www.linkedin.com/in/xavier-trinh-0a899875/
Medium Blog: https://medium.com/@xavier.nghitrinh

Professional Summary:
Data & Analytics Leader with 10+ years building platforms that turn data into competitive advantage. I architect scalable cloud solutions, pioneer AI-powered analytics, and lead teams to deliver measurable business impact—currently establishing Australia's first conversational AI analytics platform at Woolworths.

Core Competencies:
- AI & Advanced Analytics: Generative AI & LLM Integration, Multi-Agent AI Orchestration, RAG Systems, Automated Insight Generation, Predictive Analytics.
- Data Platform & Engineering: Cloud Data Architecture (GCP, AWS), BigQuery Optimisation, ETL/ELT Pipeline Design, Airflow/DAG Orchestration, Data Governance & Quality Automation.
- Business Intelligence & Visualisation: Enterprise BI Strategy, Self-Service Analytics, Dashboard Automation, Data Modelling & Semantic Layers.
- Leadership & Delivery: Roadmap Planning, Executive Stakeholder Management, Team Leadership, Agile Project Delivery.

Professional Experience:
1. Woolworths Group - WooliesX/WIQ | BI Manager (Jun 2021 - Present)
   - Architected & deployed Data Maven (conversational AI platform on Vertex AI/Cloud Run).
   - Designed parallel multi-agent orchestration pipelines for executive intelligence reporting.
   - Built billion-record source-of-truth data foundations across sales, rewards membership, partner transactions.
   - Designed BigQuery optimization strategies and automated data governance frameworks.
2. Woolworths Group - WooliesX | Lead BI Analyst (Prior to promotion - 8 months)
   - Led business unit migration from Amazon Redshift to Google Cloud Platform.
3. Woolworths Group | Senior BI Analyst (4 Years 10 Months)
   - Established centralised Redshift data warehouse & automated ETL pipelines.
4. Various Organisations | Early Career Experience (6+ Years)
   - BI Consultant & Developer across Telecommunications (Optus/Servian), Public Sector (Dept of Education), Finance (Toyota Financial Services), Retail (Myer).

Education & Certifications:
- GCP Data Analyst & BI/Looker Certifications
- MCSE: Business Intelligence
- Master of Computer Science | Bachelor of Information Technology
"""

def get_user_profile():
    try:
        db = get_firestore_client()
        doc = db.collection("settings").document(PROFILE_DOC_ID).get()
        if doc.exists:
            return doc.to_dict().get("content", DEFAULT_PROFILE)
    except Exception as e:
        print(f"Error fetching profile from Firestore: {e}")
    return DEFAULT_PROFILE

def save_user_profile(content: str):
    db = get_firestore_client()
    db.collection("settings").document(PROFILE_DOC_ID).set({
        "content": content
    })

def upload_file_to_gcs(file_path: str, destination_blob_name: str) -> str:
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        return f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"
    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        return ""

import urllib.parse

def download_file_from_gcs(blob_name: str, local_destination_path: str) -> bool:
    try:
        # Unquote URL-encoded characters and form-encoded spaces before looking up the blob.
        clean_blob_name = urllib.parse.unquote_plus(blob_name).strip("/")
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(clean_blob_name)
        os.makedirs(os.path.dirname(local_destination_path), exist_ok=True)
        blob.download_to_filename(local_destination_path)
        return True
    except Exception as e:
        print(f"Error downloading from GCS: {e}")
        return False
