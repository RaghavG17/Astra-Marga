import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class TailoringResult:
    tailored_bullets: List[str]
    truth_check: List[str]
    emphasized_skills: List[str]
    omitted_skills: List[str]
    source_map: List[dict]


class ResumeTailor:
    """
    Rewrites resume bullets to match a job description.
    Only uses experience from master_profile.json.
    Never invents skills, tools, or experience.
    """

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "llama3.2"

    def __init__(self, profile_path: str = "data/master_profile.json"):
        profile_file = Path(profile_path)
        if not profile_file.exists():
            self.profile = {"experience": [], "projects": [], "skills": {"strong": [], "medium": [], "beginner": []}}
            return
        with profile_file.open("r", encoding="utf-8") as file:
            self.profile = json.load(file)

    def _get_all_bullets(self) -> List[dict]:
        """
        Collects all real bullets from profile with their source.
        This is the only pool the AI can draw from.
        """
        bullets = []

        for exp in self.profile.get("experience", []):
            for bullet in exp.get("bullets", []):
                bullets.append({
                    "text": bullet,
                    "source": f"{exp.get('role', '')} at {exp.get('company', '')}",
                    "type": "experience",
                })

        for proj in self.profile.get("projects", []):
            for bullet in proj.get("bullets", []):
                bullets.append({
                    "text": bullet,
                    "source": proj.get("name", "Project"),
                    "type": "project",
                })

        return bullets

    def _get_all_skills(self) -> List[str]:
        skills = self.profile.get("skills", {})
        return (
            skills.get("strong", [])
            + skills.get("medium", [])
            + skills.get("beginner", [])
        )

    def _call_ollama(self, prompt: str) -> str:
        try:
            response = requests.post(
                self.OLLAMA_URL,
                json={
                    "model": self.MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 1000,
                    },
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as exc:
            return f"Error calling Ollama: {str(exc)}"

    def _build_prompt(self, job_text: str, bullets: List[dict], skills: List[str]) -> str:
        bullets_text = "\n".join([
            f"[{b['type'].upper()} - {b['source']}] {b['text']}"
            for b in bullets
        ])

        skills_text = ", ".join(skills)

        return f"""You are a resume writer helping an international student tailor their resume for a job.

STRICT RULES:
1. You can ONLY use the bullets and skills provided below. Do not invent any new experience, tools, companies, or skills.
2. Rewrite and reorder bullets to emphasize what matches the job description.
3. Keep each bullet under 2 lines.
4. Start each bullet with a strong action verb.
5. Return ONLY the rewritten bullets, one per line, starting with •
6. Do not add any explanation or commentary.

CANDIDATE SKILLS:
{skills_text}

CANDIDATE BULLETS (these are the ONLY facts you can use):
{bullets_text}

JOB DESCRIPTION:
{job_text}

Rewrite the 5 most relevant bullets from the candidate's experience to match this job.
Only pick bullets that are genuinely relevant. Do not stretch or fabricate.
Return them starting with •, one per line.
"""

    def _extract_bullets_from_response(self, response: str) -> List[str]:
        if not response or "Error calling Ollama" in response:
            return []

        lines = response.strip().split("\n")
        bullets = []
        for line in lines:
            line = line.strip()
            if line.startswith(("•", "-", "●", "*")):
                clean = line.lstrip("•-●* ").strip()
                if len(clean) > 20:
                    bullets.append(clean)
        return bullets

    def _build_truth_check(self, tailored: List[str], original_bullets: List[dict]) -> tuple:
        truth_check = []
        source_map = []

        for bullet in tailored:
            bullet_lower = bullet.lower()
            matched_source = None

            for original in original_bullets:
                orig_words = set(original["text"].lower().split())
                bullet_words = set(bullet_lower.split())
                overlap = len(orig_words & bullet_words)

                if overlap >= 5:
                    matched_source = original["source"]
                    break

            if matched_source:
                truth_check.append(f"✅ Verified: sourced from '{matched_source}'")
                source_map.append({"bullet": bullet, "source": matched_source, "verified": True})
            else:
                truth_check.append("⚠️  Review needed: could not verify source — check manually")
                source_map.append({"bullet": bullet, "source": "unknown", "verified": False})

        return truth_check, source_map

    def tailor(self, job_text: str, matched_skills: List[str], missing_skills: List[str]) -> TailoringResult:
        all_bullets = self._get_all_bullets()
        all_skills = self._get_all_skills()

        prompt = self._build_prompt(job_text, all_bullets, all_skills)
        response = self._call_ollama(prompt)

        tailored_bullets = self._extract_bullets_from_response(response)

        if not tailored_bullets:
            tailored_bullets = [b["text"] for b in all_bullets[:5]]

        truth_check, source_map = self._build_truth_check(tailored_bullets, all_bullets)

        return TailoringResult(
            tailored_bullets=tailored_bullets,
            truth_check=truth_check,
            emphasized_skills=matched_skills,
            omitted_skills=missing_skills,
            source_map=source_map,
        )


def tailor_resume(job_text: str, matched_skills: List[str], missing_skills: List[str]) -> dict:
    tailor = ResumeTailor()
    result = tailor.tailor(job_text, matched_skills, missing_skills)
    return asdict(result)


if __name__ == "__main__":
    sample_job = """
    New Grad Embedded Software Engineer at Tesla.
    Strong C++ and firmware experience required.
    Experience with STM32, UART, I2C is a plus.
    STEM OPT candidates welcome.
    """

    result = tailor_resume(sample_job, ["c++", "firmware", "uart", "i2c"], ["cuda"])
    print("\nTailored Bullets:")
    for bullet in result["tailored_bullets"]:
        print(f"  • {bullet}")
    print("\nTruth Check:")
    for check in result["truth_check"]:
        print(f"  {check}")
