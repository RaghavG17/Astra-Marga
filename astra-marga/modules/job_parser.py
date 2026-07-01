import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


COMMON_TECH_SKILLS = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c", "c#",
    "go", "rust", "kotlin", "swift", "ruby", "scala", "r",
    # Frontend
    "react", "vue", "angular", "html", "css", "next.js", "tailwind",
    # Backend
    "node", "fastapi", "flask", "django", "spring boot", "express",
    # Databases
    "sql", "postgresql", "mysql", "mongodb", "redis", "sqlite",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "ci/cd", "github actions", "jenkins", "linux", "bash",
    # AI/ML
    "machine learning", "deep learning", "tensorflow", "pytorch",
    "scikit-learn", "pandas", "numpy", "llm", "nlp", "computer vision",
    # Embedded / Hardware (good for CMPE)
    "embedded", "firmware", "rtos", "verilog", "vhdl", "fpga",
    "arduino", "raspberry pi", "uart", "spi", "i2c", "can bus",
    # General
    "git", "rest api", "graphql", "microservices", "agile", "scrum",
]

EXPERIENCE_LEVELS = {
    "new grad": ["new grad", "new graduate", "entry level", "entry-level", "0-1 year", "0 to 1 year"],
    "junior":   ["junior", "1-2 years", "1 to 2 years", "1+ year"],
    "mid":      ["mid level", "mid-level", "2-5 years", "3+ years", "2+ years"],
    "senior":   ["senior", "5+ years", "7+ years", "lead", "principal"],
    "intern":   ["intern", "internship", "co-op", "coop"],
}


@dataclass
class ParsedJob:
    title: str
    company: str
    location: str
    experience_level: str
    required_skills: List[str]
    raw_text: str


class JobParser:
    """
    Extracts structured information from a raw job description.
    No AI needed — keyword and pattern matching only.
    """

    def __init__(self):
        self.skill_list = COMMON_TECH_SKILLS

    def extract_title(self, text: str) -> str:
        common_titles = [
            "software engineer", "software developer", "frontend engineer",
            "backend engineer", "full stack engineer", "fullstack engineer",
            "data engineer", "data scientist", "ml engineer", "ai engineer",
            "machine learning engineer", "devops engineer", "cloud engineer",
            "embedded engineer", "firmware engineer", "systems engineer",
            "platform engineer", "site reliability engineer", "sre",
        ]
        text_lower = text.lower()
        for title in common_titles:
            if title in text_lower:
                return title.title()
        return "Software Engineer"

    def extract_company(self, text: str) -> str:
        patterns = [
            r"(?:about|join|at|@)\s+([A-Z][a-zA-Z0-9\s&,\.]{2,40}?)(?:\n|,|\.|is\s)",
            r"^([A-Z][a-zA-Z0-9\s&]{2,30}?)\s+is\s+(?:hiring|looking|seeking)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        return "Unknown Company"

    def extract_location(self, text: str) -> str:
        patterns = [
            r"(?:location|based in|office in|located in)[:\s]+([A-Za-z\s,]+?)(?:\n|\.|remote|hybrid)",
            r"([A-Z][a-z]+,\s*[A-Z]{2})",
            r"(remote|hybrid|on-site|onsite|in-person)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "Not specified"

    def extract_experience_level(self, text: str) -> str:
        text_lower = text.lower()
        for level, keywords in EXPERIENCE_LEVELS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return level
        return "not specified"

    def extract_skills(self, text: str) -> List[str]:
        text_lower = text.lower()
        found_skills: List[str] = []
        for skill in self.skill_list:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        return found_skills

    def parse(self, job_text: str) -> ParsedJob:
        return ParsedJob(
            title=self.extract_title(job_text),
            company=self.extract_company(job_text),
            location=self.extract_location(job_text),
            experience_level=self.extract_experience_level(job_text),
            required_skills=self.extract_skills(job_text),
            raw_text=job_text,
        )


def parse_job(job_text: str) -> Dict[str, Any]:
    parser = JobParser()
    result: ParsedJob = parser.parse(job_text)
    return asdict(result)


if __name__ == "__main__":
    sample = """
    About Nvidia
    Nvidia is hiring a New Grad Software Engineer based in Santa Clara, CA.

    We are looking for someone with strong Python and C++ skills.
    Experience with Linux, CUDA, and machine learning is a plus.
    Must be authorized to work in the United States.
    """

    result = parse_job(sample)
    print(result)