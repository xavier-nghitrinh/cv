# Cloud Run Build & Deployment Script

# 1. Enable GCP Services
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com storage.googleapis.com --project nm-prod-454707

# 2. Deploy directly from source to Cloud Run
gcloud run deploy job-app-webapp \
    --source . \
    --region australia-southeast1 \
    --project nm-prod-454707 \
    --allow-unauthenticated \
    --set-env-vars GCP_PROJECT=nm-prod-454707 \
    --set-env-vars GCS_BUCKET=job-app \
    --set-env-vars FIRESTORE_DATABASE=job-app
