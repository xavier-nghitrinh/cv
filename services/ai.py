import json
from google.genai import types
from services.gcp import get_genai_client, MODEL_NAME

SYSTEM_INSTRUCTION = "You are an Australian career consultant expert. ALL generated responses, analysis, resumes, cover letters, and application responses MUST strictly use Australian English (e.g., organisation, optimise, colour, behaviour, centre, analysed)."

def analyze_job_description(jd_text: str, user_profile: str) -> dict:
    client = get_genai_client()
    
    prompt = f"""
Analyze the following Job Description (JD) against the Candidate Profile.

Candidate Profile:
{user_profile}

Job Description:
{jd_text}

Provide a JSON object response with the following exact keys:
- "company": (string) Company or recruiting agent name
- "job_title": (string) Job title
- "contact_name": (string) Contact person name if mentioned, otherwise "N/A"
- "contact_email": (string) Contact email if mentioned, otherwise "N/A"
- "contact_phone": (string) Contact phone number if mentioned, otherwise "N/A"
- "industry": (string) Industry or sector (e.g. Retail, Commercial Real Estate, Telecommunications)
- "salary_compensation": (object) Salary and compensation estimation/extraction:
    * "estimated_base": (string) Estimated range of base annual salary in AUD (excluding bonus and superannuation) e.g. "$160,000 - $180,000 AUD base/yr", or if contractor role base daily rate e.g. "$900 - $1,100 AUD/day". Estimate based on Australian market rates for this role if not explicitly stated.
    * "stated_package": (string) Exact salary package or range if mentioned in the JD (e.g. "$180,000 + 11.5% Super + Bonus"), or "Not specified in JD" if not explicitly listed.
- "company_overview": (string) 2-3 sentences overview of the company and role context
- "match_score": (number) Match score percentage between candidate profile and JD (e.g. 85)
- "required_technical_skills": (list of short strings/tags, max 8-10 items) Key technical skills, tools, platforms, or domain knowledge requested by the JD (e.g. ["GCP", "BigQuery", "SQL", "Python", "Data Modelling"])
- "required_soft_skills": (list of short strings/tags, max 6-8 items) Key soft skills, leadership traits, or stakeholder requirements requested by the JD (e.g. ["Executive Stakeholder Management", "Team Leadership", "Agile", "Vendor Management"])
- "key_responsibilities": (list of short strings/tags, max 6-8 items) Concise key responsibilities and deliverables expected in this role (e.g. ["Lead AI Analytics Strategy", "Build RAG Pipelines", "Automate Executive Reporting", "Manage Vendor Relationships"])
- "stakeholders_and_team": (object) Key people and teams this role works with:
    * "reporting_to": (string) Manager / Reporting line if mentioned or inferred (e.g. "Head of Data & AI", "VP Technology", or "N/A")
    * "team_structure": (string) Team direct reports or peer structure (e.g. "Managing 4 Data Engineers and 2 Analysts", "Cross-functional Agile Team", or "Individual Contributor")
    * "key_stakeholders": (list of short strings/tags) Key internal/external stakeholders to partner with (e.g. ["Executive Leadership", "Regional Business Leads", "External AI Vendors", "Compliance & Risk Teams"])
- "matching_skills": (list of strings) Skills/requirements candidate possesses
- "missing_skills": (list of strings) Skills/requirements candidate lacks or needs alignment
- "job_quality_assessment": (object) Bidirectional job fit evaluation evaluated out of 10 points for each dimension:
    * "tech_stack_score": (number) Integer 1-10 rating tech stack modernity (10 = modern GCP/BigQuery/GenAI/Vertex AI, 1 = legacy Redshift/on-prem/SSRS).
    * "tech_stack_reason": (string) Brief reasoning for tech stack score.
    * "innovation_score": (number) Integer 1-10 rating innovation vs governance (10 = high innovation/pioneering AI, 1 = heavy governance/bureaucracy/admin).
    * "innovation_reason": (string) Brief reasoning for innovation vs governance score.
    * "growth_score": (number) Integer 1-10 rating self-development and technical challenge (10 = high learning/pioneering tech, 1 = boring/routine).
    * "growth_reason": (string) Brief reasoning for growth score.
    * "recommendation_score": (number) Integer 1-10 rating overall career recommendation for an AI & Data leader (10 = highly recommended, 1 = skip/not recommended).
    * "recommendation_reason": (string) Brief reasoning for overall recommendation.
    * "technical_weight_score": (number) Integer 1-10 rating technical depth vs softskills/stakeholder management (10 = heavily hands-on/technical/architecture, 1 = pure stakeholder management/politics/administration).
    * "technical_weight_reason": (string) Brief reasoning for technical vs softskills weighting.
    * "total_score": (number) Sum of the 5 scores above out of 50.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json"
        )
    )
    
    return json.loads(response.text)

def generate_custom_resume(jd_text: str, user_profile: str, custom_prompt: str) -> str:
    client = get_genai_client()
    
    prompt = f"""
Craft a highly tailored, professional Markdown Resume specifically aligned to the following Job Description (JD).

CRITICAL FORMATTING & LINK RULES:
1. Contact Header: MUST include phone number (+61) 468 664 940, email xavier.nghitrinh@gmail.com, exact LinkedIn profile link [LinkedIn](https://www.linkedin.com/in/xavier-trinh-0a899875/), and exact Medium Blog link [Medium Blog](https://medium.com/@xavier.nghitrinh). Do NOT use generic link text like "LinkedIn" without the full URL destination.
2. Clean Markdown: Do NOT include raw dividers like '---' or leftover heading markers like '####'.
3. Output ONLY clean Markdown formatted resume text suitable for conversion to HTML/PDF.
4. MUST use Australian English throughout.

Specific User Instructions / Prompts:
{custom_prompt}

Candidate Profile:
{user_profile}

Job Description:
{jd_text}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        )
    )
    return response.text

def generate_cover_letter(jd_text: str, user_profile: str, custom_prompt: str) -> str:
    client = get_genai_client()
    
    prompt = f"""
Craft a tailored, compelling Markdown Cover Letter specifically for the following Job Description (JD).
MUST use Australian English throughout. Ensure phone number (+61) 468 664 940, email xavier.nghitrinh@gmail.com, exact LinkedIn link [LinkedIn](https://www.linkedin.com/in/xavier-trinh-0a899875/), and exact Medium Blog link [Medium Blog](https://medium.com/@xavier.nghitrinh) are included in contact details.
Do NOT use raw dividers like '---' or leftover heading symbols like '####'.

Specific User Instructions / Prompts:
{custom_prompt}

Candidate Profile:
{user_profile}

Job Description:
{jd_text}

Output ONLY clean Markdown formatted cover letter text suitable for conversion to HTML/PDF.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        )
    )
    return response.text

def generate_application_answers(jd_text: str, user_profile: str, custom_prompt: str) -> str:
    client = get_genai_client()
    
    prompt = f"""
Answer specific application questions or recruiter prompts based on candidate's profile and the Job Description.
MUST use Australian English throughout.

Requirements:
- Provide short, compact, concise, and direct answers for each question or prompt.
- Do NOT use Markdown formatting (no headers, bold, italics, bullet asterisks, or markdown symbols).
- Output plain raw text only so it can be copied and pasted directly into an online application form field.
- Separate each question and answer pair with a simple line space if multiple questions are present.

Recruiter Prompts / Questions / Instructions:
{custom_prompt}

Candidate Profile:
{user_profile}

Job Description:
{jd_text}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        )
    )
    return response.text
