#!/usr/bin/env python3
"""
Seed the knowledge base with visa guidance and admission requirement content.
Run once after db init: python scripts/seed_knowledge.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import AsyncSessionLocal
from app.services.rag import seed_knowledge_base

KNOWLEDGE_ENTRIES = [
    # ── UK ────────────────────────────────────────────────────────────────────
    {
        "topic": "visa_uk",
        "country": "UK",
        "content": (
            "UK Student visa (formerly Tier 4) requirements: You need a Confirmation of Acceptance "
            "for Studies (CAS) from a licensed UK university. IELTS minimum is typically 5.5–6.5 "
            "overall depending on course level. Funds required: £1,334/month for London, £1,023/month "
            "outside London, held for 28 consecutive days before application. Application fee: £363 "
            "outside UK. Healthcare surcharge: £776/year. Biometrics required at a visa application centre. "
            "Decision time: 3 weeks inside UK, 3 weeks outside. CAS must be used within 6 months."
        ),
    },
    {
        "topic": "visa_interview_uk",
        "country": "UK",
        "content": (
            "UK student visa interviews are rare but can be requested. Common embassy interview questions: "
            "Why this university specifically? Why this course? What are your career plans after graduation? "
            "Do you have family or assets in your home country (ties)? How will you fund your studies? "
            "Have you studied English formally? Strong answers show genuine academic intent, realistic career "
            "plans tied to your home country's industry, and documented financial capacity. Vague or rehearsed "
            "answers about 'gaining experience' without specifics are a red flag."
        ),
    },
    {
        "topic": "checklist_uk",
        "country": "UK",
        "content": (
            "UK student visa document checklist: (1) Valid passport (6+ months beyond course end). "
            "(2) CAS reference number from university. (3) Bank statements showing required funds for "
            "28 consecutive days. (4) IELTS/TOEFL certificate. (5) Academic transcripts. "
            "(6) Tuberculosis test result if applicable (Bangladesh requires this). "
            "(7) ATAS clearance certificate if studying certain science/tech subjects. "
            "(8) Parental consent letter if under 18. Documents must be in English or officially translated."
        ),
    },
    # ── Canada ────────────────────────────────────────────────────────────────
    {
        "topic": "visa_canada",
        "country": "Canada",
        "content": (
            "Canadian Student Permit requirements: Acceptance letter from a Designated Learning Institution (DLI). "
            "Proof of funds: CAD 10,000/year for living expenses plus first year tuition. IELTS minimum 6.0 "
            "overall for most universities. Processing time: 8–12 weeks online, longer for paper applications. "
            "Application fee: CAD 150. Biometrics fee: CAD 85. SDS (Student Direct Stream) available for "
            "Bangladesh applicants: requires IELTS 6.0, GIC of CAD 10,000, and paid first year tuition — "
            "reduces processing to ~20 days. PAL (Provincial Attestation Letter) now required for most "
            "undergraduate applications."
        ),
    },
    {
        "topic": "checklist_canada",
        "country": "Canada",
        "content": (
            "Canada student permit document checklist: (1) Valid passport. (2) Acceptance letter from DLI. "
            "(3) Proof of funds (GIC from approved bank for SDS stream, or bank statements). "
            "(4) IELTS certificate (6.0+ overall). (5) Academic transcripts (notarised). "
            "(6) Statement of purpose explaining study plan and intent to return home. "
            "(7) PAL from provincial government (for UG programs at most provinces). "
            "(8) Medical exam if required. (9) Police clearance certificate. "
            "SDS applicants also need: IELTS, GIC confirmation, and paid tuition receipt."
        ),
    },
    # ── Australia ─────────────────────────────────────────────────────────────
    {
        "topic": "visa_australia",
        "country": "Australia",
        "content": (
            "Australian Student visa (subclass 500) requirements: Confirmation of Enrolment (CoE) from a "
            "registered CRICOS provider. Genuine Student requirement: you must demonstrate genuine intent to "
            "study. IELTS minimum: 5.5–6.5 depending on institution and course. Funds: AUD 24,505/year "
            "(2024 rate). Application fee: AUD 710. Health insurance (OSHC) mandatory for entire stay. "
            "GTE (Genuine Temporary Entrant) statement required — explain why you chose Australia, this "
            "institution, and this course, and your ties to home country. Assessment level 1–3 based on "
            "country — Bangladesh is typically Level 2 or 3, requiring stronger documentation."
        ),
    },
    {
        "topic": "checklist_australia",
        "country": "Australia",
        "content": (
            "Australia student visa checklist: (1) CoE from CRICOS institution. (2) Valid passport. "
            "(3) IELTS/PTE/TOEFL certificate. (4) Academic transcripts. (5) Financial evidence "
            "(bank statements or scholarship letter). (6) GTE statement (500–800 words). "
            "(7) OSHC health insurance. (8) Health examination results. (9) Character documents "
            "(police clearance). (10) Evidence of ties to home country (property, family, job offer). "
            "For AUS Level 2/3 countries: stronger financial evidence and detailed GTE are critical "
            "to avoid refusal."
        ),
    },
    # ── Germany ───────────────────────────────────────────────────────────────
    {
        "topic": "visa_germany",
        "country": "Germany",
        "content": (
            "German student visa requirements: Unconditional admission letter from a German university "
            "(or Zulassung). Blocked account (Sperrkonto) with €11,208 (2024 rate, ~€934/month). "
            "German language B2 or English B2 certificate depending on programme language. "
            "Application at German embassy — wait times can be 6–12 weeks in Dhaka. "
            "Health insurance from German statutory provider required upon arrival. "
            "APS certificate (Academic Evaluation Centre) mandatory for Bangladeshi students — "
            "submit transcripts to APS Dhaka office, process takes 4–6 weeks. Without APS, "
            "university application will not be accepted."
        ),
    },
    {
        "topic": "checklist_germany",
        "country": "Germany",
        "content": (
            "Germany student visa checklist: (1) Valid passport. (2) University admission letter. "
            "(3) APS certificate (mandatory for Bangladesh). (4) Blocked account (Sperrkonto) confirmation. "
            "(5) Language certificate (German B2 or English B2/C1). (6) Academic transcripts (certified). "
            "(7) Motivation letter. (8) CV/Resume. (9) Health insurance confirmation. "
            "(10) Biometric photos. (11) Visa application form. (12) Embassy appointment confirmation. "
            "APS must be obtained before applying to university. Start APS process at least 3 months "
            "before intended application deadline."
        ),
    },
    # ── General admission ─────────────────────────────────────────────────────
    {
        "topic": "sop_guidance",
        "country": "GENERAL",
        "content": (
            "A strong Statement of Purpose (SOP) must address: (1) Why this specific university and programme "
            "— reference specific faculty, research groups, or curriculum modules. (2) Your academic background "
            "and how it prepares you for this programme. (3) Professional experience and skills gained. "
            "(4) Your research interest or career goal and how this degree advances it. (5) Your long-term "
            "plan and how you will use this degree in your home country or career. Avoid generic phrases like "
            "'I have always been passionate about'. Be specific with numbers, project names, results. "
            "Typical length: 600–1000 words. Address any weaknesses (gap years, lower GPA) proactively."
        ),
    },
    {
        "topic": "ielts_guidance",
        "country": "GENERAL",
        "content": (
            "IELTS score requirements by country and level: UK undergraduate: 5.5–6.0 overall; "
            "UK postgraduate: 6.0–6.5 overall, 6.0 in writing. Canada: 6.0–6.5 overall. "
            "Australia: 5.5–6.5 depending on institution level. Germany (English programmes): 6.0–6.5. "
            "USA: 6.5–7.0 for competitive schools. Writing band is often separately assessed — "
            "a 5.0 writing band can disqualify even with a higher overall. IELTS is valid for 2 years. "
            "Academic IELTS required (not General Training) for all university applications."
        ),
    },
    {
        "topic": "financial_proof",
        "country": "GENERAL",
        "content": (
            "Financial proof requirements vary by country. General principles: (1) Bank statements must show "
            "consistent balance over 3–6 months, not a single large recent deposit. (2) Source of funds "
            "must be explainable — salary, business income, property sale, scholarship. (3) Sponsor letters "
            "must be notarised and accompanied by sponsor's financial documents. (4) Scholarship letters from "
            "the university are strong evidence. (5) For UK: 28 consecutive days rule — funds must be in "
            "account for exactly 28 days before application date. (6) For blocked accounts (Germany): "
            "funds are deposited with a German bank (Fintiba, Deutsche Bank) and can only be withdrawn "
            "monthly after arrival."
        ),
    },
]


async def main():
    async with AsyncSessionLocal() as db:
        count = await seed_knowledge_base(KNOWLEDGE_ENTRIES, db)
        print(f"Seeded {count} knowledge base entries.")


if __name__ == "__main__":
    asyncio.run(main())
