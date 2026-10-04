import os
import re
import urllib.parse
from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from services.gcp import get_firestore_client, FIRESTORE_COLLECTION, GCS_BUCKET_NAME
from services.profile import get_user_profile, save_user_profile, upload_file_to_gcs, download_file_from_gcs
from services.ai import analyze_job_description, generate_custom_resume, generate_cover_letter, generate_application_answers
from services.pdf import convert_md_to_pdf

app = FastAPI(title="Job Application Assistant")

templates = Jinja2Templates(directory="templates")

# Local output folder for PDFs
LOCAL_OUTPUT_DIR = os.path.join(os.getcwd(), "output")
os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)

def sanitize_filename(text: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', text or "")
    cleaned = cleaned.strip("._-")
    cleaned = re.sub(r'_+', '_', cleaned)
    return cleaned or "document"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    db = get_firestore_client()
    docs = db.collection(FIRESTORE_COLLECTION).stream()
    
    applications = []
    for doc in docs:
        d = doc.to_dict()
        if d.get("is_deleted") is True:
            continue
        d["id"] = doc.id
        applications.append(d)
        
    applications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return templates.TemplateResponse(request=request, name="index.html", context={"applications": applications})

@app.get("/new", response_class=HTMLResponse)
async def new_application_page(request: Request):
    return templates.TemplateResponse(request=request, name="new.html")

@app.post("/new")
async def create_new_application(jd_text: str = Form(...)):
    user_profile = get_user_profile()
    analysis = analyze_job_description(jd_text, user_profile)
    
    company = analysis.get("company", "Unknown")
    job_title = analysis.get("job_title", "Unknown Role")
    contact_name = analysis.get("contact_name", "N/A")
    contact_email = analysis.get("contact_email", "N/A")
    contact_phone = analysis.get("contact_phone", "N/A")
    industry = analysis.get("industry", "N/A")
    company_overview = analysis.get("company_overview", "")
    match_score = analysis.get("match_score", 0)
    required_technical_skills = analysis.get("required_technical_skills", [])
    required_soft_skills = analysis.get("required_soft_skills", [])
    key_responsibilities = analysis.get("key_responsibilities", [])
    stakeholders_and_team = analysis.get("stakeholders_and_team", {})
    salary_compensation = analysis.get("salary_compensation", {})
    matching_skills = analysis.get("matching_skills", [])
    missing_skills = analysis.get("missing_skills", [])
    job_quality_assessment = analysis.get("job_quality_assessment", {})
    
    db = get_firestore_client()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    doc_ref = db.collection(FIRESTORE_COLLECTION).document()
    doc_data = {
        "company": company,
        "job_title": job_title,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "industry": industry,
        "company_overview": company_overview,
        "match_score": match_score,
        "required_technical_skills": required_technical_skills,
        "required_soft_skills": required_soft_skills,
        "key_responsibilities": key_responsibilities,
        "stakeholders_and_team": stakeholders_and_team,
        "salary_compensation": salary_compensation,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "job_quality_assessment": job_quality_assessment,
        "jd_text": jd_text,
        "created_at": now_str,
        "is_deleted": False,
        "resume_md": "",
        "resume_pdf_path": "",
        "resume_gcs_uri": "",
        "cl_md": "",
        "cl_pdf_path": "",
        "cl_gcs_uri": "",
        "questions_md": "",
        "questions_pdf_path": "",
        "questions_gcs_uri": ""
    }
    doc_ref.set(doc_data)
    
    return RedirectResponse(url=f"/application/{doc_ref.id}", status_code=303)

ADMIN_PASSPHRASE = os.environ.get("ADMIN_PASSPHRASE", "tumlumtala")

@app.get("/application/{app_id}", response_class=HTMLResponse)
async def application_detail(request: Request, app_id: str, delete_error: str = None):
    db = get_firestore_client()
    doc = db.collection(FIRESTORE_COLLECTION).document(app_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_data = doc.to_dict()
    if app_data.get("is_deleted") is True:
        raise HTTPException(status_code=404, detail="Application has been deleted")
        
    app_data["id"] = doc.id
    
    return templates.TemplateResponse(request=request, name="application_detail.html", context={"app": app_data, "delete_error": delete_error})

@app.post("/application/{app_id}/delete")
async def delete_application(request: Request, app_id: str, passphrase: str = Form(...)):
    if passphrase != ADMIN_PASSPHRASE:
        db = get_firestore_client()
        doc = db.collection(FIRESTORE_COLLECTION).document(app_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Application not found")
        app_data = doc.to_dict()
        app_data["id"] = doc.id
        return templates.TemplateResponse(request=request, name="application_detail.html", context={
            "app": app_data,
            "delete_error": "Invalid passphrase. Application was not deleted."
        }, status_code=400)
        
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(app_id)
    doc_ref.update({
        "is_deleted": True
    })
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/application/{app_id}/generate-resume")
async def handle_generate_resume(app_id: str, resume_prompt: str = Form("")):
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(app_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_data = doc.to_dict()
    user_profile = get_user_profile()
    
    resume_md = generate_custom_resume(app_data["jd_text"], user_profile, resume_prompt)
    
    safe_company = sanitize_filename(app_data["company"])
    safe_title = sanitize_filename(app_data["job_title"])
    filename = f"{safe_company}_{safe_title}_cv.pdf"
    
    local_path = os.path.join(LOCAL_OUTPUT_DIR, filename)
    convert_md_to_pdf(resume_md, local_path)
    
    gcs_blob_name = f"applications/{app_id}/{filename}"
    gcs_uri = upload_file_to_gcs(local_path, gcs_blob_name)
    
    doc_ref.update({
        "resume_md": resume_md,
        "resume_pdf_path": local_path,
        "resume_gcs_uri": gcs_uri
    })
    
    return {
        "status": "success",
        "resume_md": resume_md,
        "resume_pdf_path": local_path,
        "resume_gcs_uri": gcs_uri,
        "download_url": f"/download?path={urllib.parse.quote(local_path)}&gcs_blob={urllib.parse.quote(f'applications/{app_id}/{filename}')}"
    }

@app.post("/application/{app_id}/generate-cover-letter")
async def handle_generate_cover_letter(app_id: str, cl_prompt: str = Form("")):
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(app_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_data = doc.to_dict()
    user_profile = get_user_profile()
    
    cl_md = generate_cover_letter(app_data["jd_text"], user_profile, cl_prompt)
    
    safe_company = sanitize_filename(app_data["company"])
    safe_title = sanitize_filename(app_data["job_title"])
    filename = f"{safe_company}_{safe_title}_cl.pdf"
    
    local_path = os.path.join(LOCAL_OUTPUT_DIR, filename)
    convert_md_to_pdf(cl_md, local_path)
    
    gcs_blob_name = f"applications/{app_id}/{filename}"
    gcs_uri = upload_file_to_gcs(local_path, gcs_blob_name)
    
    doc_ref.update({
        "cl_md": cl_md,
        "cl_pdf_path": local_path,
        "cl_gcs_uri": gcs_uri
    })
    
    return {
        "status": "success",
        "cl_md": cl_md,
        "cl_pdf_path": local_path,
        "cl_gcs_uri": gcs_uri,
        "download_url": f"/download?path={urllib.parse.quote(local_path)}&gcs_blob={urllib.parse.quote(f'applications/{app_id}/{filename}')}"
    }

@app.post("/application/{app_id}/generate-questions")
async def handle_generate_questions(app_id: str, questions_prompt: str = Form(...)):
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(app_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_data = doc.to_dict()
    user_profile = get_user_profile()
    
    questions_text = generate_application_answers(app_data["jd_text"], user_profile, questions_prompt)
    
    from datetime import datetime
    new_entry = {
        "id": f"q_{int(datetime.utcnow().timestamp())}",
        "prompt": questions_prompt,
        "answer": questions_text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    existing_log = app_data.get("questions_log", [])
    existing_log.insert(0, new_entry)
    
    doc_ref.update({
        "questions_log": existing_log,
        "questions_md": questions_text  # maintain backwards compatibility
    })
    
    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

@app.post("/application/{app_id}/delete-question/{entry_id}")
async def handle_delete_question(app_id: str, entry_id: str):
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(app_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_data = doc.to_dict()
    existing_log = app_data.get("questions_log", [])
    updated_log = [item for item in existing_log if item.get("id") != entry_id]
    
    doc_ref.update({
        "questions_log": updated_log
    })
    
    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

@app.post("/application/{app_id}/reassess")
async def handle_reassess_application(app_id: str):
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(app_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_data = doc.to_dict()
    jd_text = app_data.get("jd_text", "")
    if not jd_text:
        raise HTTPException(status_code=400, detail="Job description (JD) text is missing for this application.")
        
    user_profile = get_user_profile()
    analysis = analyze_job_description(jd_text, user_profile)
    
    doc_ref.update({
        "company": analysis.get("company", app_data.get("company", "Unknown")),
        "job_title": analysis.get("job_title", app_data.get("job_title", "Unknown Role")),
        "contact_name": analysis.get("contact_name", app_data.get("contact_name", "N/A")),
        "contact_email": analysis.get("contact_email", app_data.get("contact_email", "N/A")),
        "contact_phone": analysis.get("contact_phone", app_data.get("contact_phone", "N/A")),
        "industry": analysis.get("industry", "N/A"),
        "company_overview": analysis.get("company_overview", ""),
        "match_score": analysis.get("match_score", 0),
        "required_technical_skills": analysis.get("required_technical_skills", []),
        "required_soft_skills": analysis.get("required_soft_skills", []),
        "key_responsibilities": analysis.get("key_responsibilities", []),
        "stakeholders_and_team": analysis.get("stakeholders_and_team", {}),
        "salary_compensation": analysis.get("salary_compensation", {}),
        "matching_skills": analysis.get("matching_skills", []),
        "missing_skills": analysis.get("missing_skills", []),
        "job_quality_assessment": analysis.get("job_quality_assessment", {})
    })
    
    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

@app.post("/application/{app_id}/update-contact")
async def update_contact_info(
    app_id: str,
    contact_name: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form("")
):
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(app_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Application not found")
        
    doc_ref.update({
        "contact_name": contact_name.strip() or "N/A",
        "contact_email": contact_email.strip() or "N/A",
        "contact_phone": contact_phone.strip() or "N/A"
    })
    
    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
async def edit_profile_page(request: Request, updated: bool = False):
    profile_text = get_user_profile()
    return templates.TemplateResponse(request=request, name="profile.html", context={"profile_text": profile_text, "updated": updated})

@app.post("/profile")
async def update_profile(content: str = Form(...)):
    save_user_profile(content)
    return RedirectResponse(url="/profile?updated=true", status_code=303)

@app.get("/download")
async def download_file(path: str, gcs_blob: str = None):
    # Normalize paths for local lookup
    clean_path = urllib.parse.unquote_plus(path)
    
    # If running locally on Windows and path is /app/output/..., remap to local output folder
    if not os.path.exists(clean_path):
        filename = os.path.basename(clean_path)
        local_alt_path = os.path.join(LOCAL_OUTPUT_DIR, filename)
        if os.path.exists(local_alt_path):
            return FileResponse(local_alt_path, filename=filename, media_type="application/pdf")
        target_save_path = local_alt_path
    else:
        target_save_path = clean_path
        filename = os.path.basename(clean_path)
    
    # 2. Try directly specified gcs_blob parameter
    if gcs_blob:
        clean_gcs_blob = urllib.parse.unquote_plus(gcs_blob)
        if download_file_from_gcs(clean_gcs_blob, target_save_path):
            return FileResponse(target_save_path, filename=filename, media_type="application/pdf")
            
    # 3. Fallback: Search Firestore applications to find matching gcs_uri or blob name
    db = get_firestore_client()
    docs = db.collection(FIRESTORE_COLLECTION).stream()
    for doc in docs:
        d = doc.to_dict()
        app_id = doc.id
        
        # Check resume matches
        if d.get("resume_pdf_path") in (path, clean_path) or os.path.basename(d.get("resume_pdf_path", "")) == filename:
            blob_name = d.get("resume_gcs_uri", "").replace(f"gs://{GCS_BUCKET_NAME}/", "") if d.get("resume_gcs_uri") else f"applications/{app_id}/{filename}"
            if download_file_from_gcs(blob_name, target_save_path):
                return FileResponse(target_save_path, filename=filename, media_type="application/pdf")
                
        # Check cover letter matches
        if d.get("cl_pdf_path") in (path, clean_path) or os.path.basename(d.get("cl_pdf_path", "")) == filename:
            blob_name = d.get("cl_gcs_uri", "").replace(f"gs://{GCS_BUCKET_NAME}/", "") if d.get("cl_gcs_uri") else f"applications/{app_id}/{filename}"
            if download_file_from_gcs(blob_name, target_save_path):
                return FileResponse(target_save_path, filename=filename, media_type="application/pdf")

    raise HTTPException(status_code=404, detail="File not found")
