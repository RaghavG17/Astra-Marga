import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import requests


@dataclass
class OutreachResult:
    recruiter_message: str
    alumni_message: str
    hiring_manager_message: str
    follow_up_message: str
    search_suggestions: List[str]


class OutreachDrafter:
    """Drafts personalized messages; all messages are reviewed and sent manually."""

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "llama3.2"

    def __init__(self, profile_path: str = "data/master_profile.json") -> None:
        path = Path(profile_path)
        self.profile = {}
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                self.profile = json.load(file)

    def _call_ollama(self, prompt: str) -> str:
        response = requests.post(
            self.OLLAMA_URL,
            json={
                "model": self.MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 400},
            },
            timeout=60,
        )
        response.raise_for_status()
        message = response.json().get("response", "").strip()
        if not message:
            raise ValueError("Ollama returned an empty outreach message.")
        return message

    def _fallback_message(
        self, message_type: str, company: str, role: str, matched_skills: List[str]
    ) -> str:
        name = self.profile.get("name", "")
        school = self.profile.get("school", "")
        graduation = self.profile.get("graduation", "")
        skills = ", ".join(matched_skills[:3]) or "relevant skills"

        if message_type == "recruiter":
            return (
                f"Hi [Name],\n\nI came across the {role} role at {company} and wanted "
                f"to reach out. I'm a Computer Engineering student at {school}, "
                f"graduating {graduation}, with experience in {skills}.\n\n"
                "I'm currently on F-1 OPT and looking for new grad roles. Would love "
                "to learn more about this position and whether it could be a fit.\n\n"
                f"Best,\n{name}"
            )
        if message_type == "alumni":
            return (
                f"Hi [Name],\n\nI noticed you're at {company} — I'm also a {school} "
                f"student graduating {graduation}. I'm interested in the {role} role "
                "and would love to hear about your experience there.\n\n"
                "Would you have 15 minutes for a quick chat? I'd really appreciate "
                f"any advice.\n\nBest,\n{name}"
            )
        if message_type == "hiring_manager":
            return (
                f"Hi [Name],\n\nI'm reaching out about the {role} position at {company}. "
                f"My background in {skills} aligns well with the team's work, and I'm "
                "excited about the opportunity.\n\n"
                f"I'm a {school} Computer Engineering graduate ({graduation}) on F-1 "
                f"OPT. Happy to share more about my work if helpful.\n\nBest,\n{name}"
            )
        return (
            f"Hi [Name],\n\nI wanted to follow up on my application for the {role} role "
            f"at {company}. I'm still very interested and would love to discuss how "
            f"I can contribute.\n\nBest,\n{name}"
        )

    def _build_prompt(
        self,
        message_type: str,
        company: str,
        role: str,
        matched_skills: List[str],
        job_text: str,
    ) -> str:
        name = self.profile.get("name", "")
        school = self.profile.get("school", "")
        graduation = self.profile.get("graduation", "")
        skills = ", ".join(matched_skills[:5])
        instructions = {
            "recruiter": "under 100 words; professional and warm; mention F-1 OPT naturally; end with a clear ask",
            "alumni": "under 80 words; warm peer-to-peer tone; mention the shared school; ask for a 15-minute chat",
            "hiring_manager": "under 100 words; confident but not arrogant; lead with specific value",
            "follow_up": "under 60 words; polite and not pushy; reiterate interest briefly",
        }
        return (
            f"Write a LinkedIn {message_type} message. Candidate: {name}; school: "
            f"{school}; graduating: {graduation}; role: {role} at {company}; "
            f"matched skills: {skills}. Job description: {job_text[:3000]}\n"
            f"Rules: {instructions[message_type]}. Return only the message."
        )

    def _get_search_suggestions(self, company: str, role: str) -> List[str]:
        return [
            f"{company} recruiter university hiring",
            f"{company} software engineer new grad",
            f"{company} SJSU alumni",
            f"{company} engineering manager",
            f"{company} campus recruiter",
        ]

    def draft(
        self,
        company: str,
        role: str,
        matched_skills: List[str],
        job_text: str,
        use_ai: bool = True,
    ) -> OutreachResult:
        messages = {}
        message_types = ("recruiter", "alumni", "hiring_manager", "follow_up")
        for message_type in message_types:
            if use_ai:
                try:
                    messages[message_type] = self._call_ollama(
                        self._build_prompt(
                            message_type, company, role, matched_skills, job_text
                        )
                    )
                except (requests.RequestException, ValueError):
                    messages[message_type] = self._fallback_message(
                        message_type, company, role, matched_skills
                    )
            else:
                messages[message_type] = self._fallback_message(
                    message_type, company, role, matched_skills
                )

        return OutreachResult(
            recruiter_message=messages["recruiter"],
            alumni_message=messages["alumni"],
            hiring_manager_message=messages["hiring_manager"],
            follow_up_message=messages["follow_up"],
            search_suggestions=self._get_search_suggestions(company, role),
        )


def draft_outreach(
    company: str,
    role: str,
    matched_skills: List[str],
    job_text: str,
    use_ai: bool = True,
) -> dict:
    return asdict(
        OutreachDrafter().draft(company, role, matched_skills, job_text, use_ai)
    )
