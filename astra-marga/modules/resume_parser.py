import json
import re
from pathlib import Path

import pdfplumber
from docx import Document

from modules.job_parser import COMMON_TECH_SKILLS

# Skills from YOUR resume specifically
STRONG_SKILLS = [
    "c++", "c", "python", "stm32", "freertos", "i2c", "spi", "uart",
    "arduino", "esp32", "firmware", "embedded", "react", "sql",
    "fastapi", "mongodb", "firebase", "git", "linux", "next.js"
]

MEDIUM_SKILLS = [
    "flutter", "dart", "verilog", "fpga", "ros", "assembly",
    "wireshark", "vmware", "c#", "uml", "rest api"
]

BEGINNER_SKILLS = [
    "aws", "docker", "kubernetes", "machine learning", "tensorflow"
]


def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_skills_with_levels(text: str) -> dict:
    text_lower = text.lower()
    strong, medium, beginner = [], [], []

    for skill in COMMON_TECH_SKILLS:
        if skill.lower() in text_lower:
            if skill.lower() in STRONG_SKILLS:
                strong.append(skill)
            elif skill.lower() in MEDIUM_SKILLS:
                medium.append(skill)
            elif skill.lower() in BEGINNER_SKILLS:
                beginner.append(skill)
            else:
                medium.append(skill)  # default to medium if found but uncategorized

    return {
        "strong": list(set(strong)),
        "medium": list(set(medium)),
        "beginner": list(set(beginner)),
    }


def extract_section(text: str, start_keywords: list, end_keywords: list) -> str:
    lines = text.split("\n")
    capturing = False
    section_lines = []

    for line in lines:
        line_lower = line.strip().lower()

        if any(kw in line_lower for kw in start_keywords):
            capturing = True
            continue

        if capturing and any(kw in line_lower for kw in end_keywords):
            break

        if capturing and line.strip():
            section_lines.append(line.strip())

    return "\n".join(section_lines)


def extract_bullets_from_section(section_text: str) -> list:
    lines = section_text.split("\n")
    bullets = []
    for line in lines:
        line = line.strip()
        # Only grab lines that look like real resume bullets.
        if line and (
            line.startswith(("●", "•", "-", "▪", "*")) or
            re.match(r"^(Developed|Implemented|Designed|Built|Led|Created|Managed|Conducted|Architected|Collaborated|Utilized|Identified)", line)
        ):
            clean = line.lstrip("●•-▪* ").strip()
            if len(clean) > 20:
                bullets.append(clean)
    return bullets


def extract_projects(text: str) -> list:
    project_section = extract_section(
        text,
        start_keywords=["projects"],
        end_keywords=["leadership", "education", "skills", "work experience"],
    )

    projects = []
    current_project = None
    lines = project_section.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Project title lines usually have a date range
        if re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}", line):
            if current_project:
                projects.append(current_project)
            # Extract just the project name (before the date)
            name = re.split(r",\s*\w+\s+\d{4}", line)[0].strip()
            current_project = {"name": name, "skills": [], "bullets": []}

        elif current_project and line.startswith(("●", "•", "-")):
            bullet = line.lstrip("●•- ").strip()
            if len(bullet) > 20:
                current_project["bullets"].append(bullet)

    if current_project:
        projects.append(current_project)

    return projects


def extract_experience(text: str) -> list:
    exp_section = extract_section(
        text,
        start_keywords=["work experience", "experience"],
        end_keywords=["projects", "leadership", "education"],
    )

    experience = []
    current_exp = None
    lines = exp_section.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}", line):
            if current_exp:
                experience.append(current_exp)
            parts = line.split(",")
            role = parts[0].strip() if parts else line
            company = parts[1].strip() if len(parts) > 1 else ""
            current_exp = {"role": role, "company": company, "bullets": []}

        elif current_exp and line.startswith(("●", "•", "-")):
            bullet = line.lstrip("●•- ").strip()
            if len(bullet) > 20:
                current_exp["bullets"].append(bullet)

    if current_exp:
        experience.append(current_exp)

    return experience


def parse_resume(file_path: str) -> dict:
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif path.suffix.lower() in [".docx", ".doc"]:
        text = extract_text_from_docx(file_path)
    else:
        return {}

    skills = extract_skills_with_levels(text)
    projects = extract_projects(text)
    experience = extract_experience(text)

    profile = {
        "name": "Raghav Gautam",
        "school": "San Jose State University",
        "degree": "Computer Engineering",
        "graduation": "December 2026",
        "work_authorization": {
            "status": "F-1",
            "seeking_opt_friendly_roles": True,
            "future_sponsorship_needed": True,
        },
        "target_roles": [
            "Software Engineer New Grad",
            "Embedded Software Engineer",
            "Firmware Engineer",
            "Full Stack Engineer",
        ],
        "skills": skills,
        "projects": projects,
        "experience": experience,
    }

    return profile


def save_profile(profile: dict, output_path: str = "data/master_profile.json"):
    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)
    return output_path
