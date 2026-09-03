import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.job_parser import parse_job


@dataclass
class ScoringResult:
    match_score: int
    visa_adjusted_score: int
    decision: str
    matched_skills: List[str]
    missing_skills: List[str]
    reasoning: List[str]
    experience_level_fit: str


class JobScorer:
    """
    Compares a parsed job against the candidate's master profile.
    No AI needed — pure rule-based scoring.
    """

    def __init__(self, profile_path: str = "data/master_profile.json"):
        self.profile = self._load_profile(profile_path)
        self.all_skills = self._get_all_skills()

    def _load_profile(self, path: str) -> dict:
        profile_path = Path(path)
        if not profile_path.exists():
            return {"skills": {"strong": [], "medium": [], "beginner": []}}

        with profile_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _get_all_skills(self) -> dict:
        skills = self.profile.get("skills", {})
        return {
            "strong": [s.lower() for s in skills.get("strong", [])],
            "medium": [s.lower() for s in skills.get("medium", [])],
            "beginner": [s.lower() for s in skills.get("beginner", [])],
        }

    def _score_skills(self, required_skills: List[str]) -> tuple:
        matched = []
        missing = []
        score = 0

        for skill in required_skills:
            skill_lower = skill.lower()
            if skill_lower in self.all_skills["strong"]:
                matched.append(skill)
                score += 10
            elif skill_lower in self.all_skills["medium"]:
                matched.append(skill)
                score += 6
            elif skill_lower in self.all_skills["beginner"]:
                matched.append(skill)
                score += 3
            else:
                missing.append(skill)

        return matched, missing, score

    def _get_candidate_level(self) -> str:
        """
        Infers candidate level from their profile automatically.
        Works for any user — freshman, junior, senior, new grad.
        """
        experience = self.profile.get("experience", [])
        projects = self.profile.get("projects", [])
        strong_skills = self.all_skills["strong"]

        work_count = len(experience)
        project_count = len(projects)
        skill_count = len(strong_skills)

        if work_count >= 2 and skill_count >= 10:
            return "mid"
        elif work_count >= 1 or project_count >= 3:
            return "new grad"
        elif project_count >= 1:
            return "junior"
        else:
            return "freshman"

    def _score_experience_level(self, job_level: str) -> tuple:
        """
        Scores how well the job level fits the candidate's actual level.
        Dynamically inferred — works for any user.
        """
        candidate_level = self._get_candidate_level()

        level_map = {
            "freshman": 0,
            "junior": 1,
            "new grad": 2,
            "mid": 3,
            "senior": 4,
        }

        job_level_rank = level_map.get(job_level, 2)
        candidate_rank = level_map.get(candidate_level, 2)
        diff = job_level_rank - candidate_rank

        if diff == 0:
            return 20, "good", f"Role matches your level ({candidate_level})"
        elif diff == 1:
            return 12, "stretch", f"Role is one level above you ({candidate_level} → {job_level}) — worth trying"
        elif diff == -1:
            return 15, "good", f"Role is slightly below your level — easy apply"
        elif diff >= 2:
            return 0, "poor", f"Role requires significantly more experience than you have ({candidate_level} vs {job_level})"
        else:
            return 10, "overqualified", f"You may be overqualified for this role"

    def _make_decision(self, match_score: int, visa_score: int) -> str:
        if visa_score <= 25:
            return "Skip"
        elif match_score >= 70 and visa_score >= 50:
            return "Apply"
        elif match_score >= 45:
            return "Maybe"
        else:
            return "Skip"

    def score(self, job_text: str, visa_result: dict) -> ScoringResult:
        parsed = parse_job(job_text)
        required_skills = parsed["required_skills"]

        matched, missing, skill_score = self._score_skills(required_skills)
        exp_score, exp_fit, exp_reasoning = self._score_experience_level(
            parsed["experience_level"]
        )

        max_skill_score = len(required_skills) * 10 if required_skills else 1
        normalized_skill_score = int((skill_score / max_skill_score) * 80)
        normalized_skill_score = min(normalized_skill_score, 80)

        match_score = normalized_skill_score + exp_score
        match_score = min(match_score, 100)

        visa_score = visa_result.get("score", 50)
        visa_adjusted = int((match_score * 0.6) + (visa_score * 0.4))

        decision = self._make_decision(match_score, visa_score)

        reasoning = []
        if matched:
            reasoning.append(f"✅ Matched {len(matched)} skills: {', '.join(matched[:5])}")
        if missing:
            reasoning.append(f"⚠️ Missing {len(missing)} skills: {', '.join(missing[:5])}")
        reasoning.append(f"📊 Experience level: {exp_reasoning}")
        if visa_result.get("red_flags"):
            reasoning.append(f"🚨 Visa red flags: {', '.join(visa_result['red_flags'][:2])}")
        if visa_result.get("positive_signals"):
            reasoning.append(f"✅ Visa positive: {', '.join(visa_result['positive_signals'][:2])}")

        return ScoringResult(
            match_score=match_score,
            visa_adjusted_score=visa_adjusted,
            decision=decision,
            matched_skills=matched,
            missing_skills=missing,
            reasoning=reasoning,
            experience_level_fit=exp_fit,
        )


def score_job(job_text: str, visa_result: dict) -> dict:
    scorer = JobScorer()
    result = scorer.score(job_text, visa_result)
    return asdict(result)


if __name__ == "__main__":
    sample_job = """
    Nvidia is hiring a New Grad Software Engineer in Santa Clara, CA.
    Strong C++ and Python skills required. Experience with Linux and
    embedded systems is a plus. We welcome STEM OPT candidates and
    offer H-1B sponsorship.
    """

    from modules.visa_detector import analyze_visa_language

    visa = analyze_visa_language(sample_job)
    result = score_job(sample_job, visa)

    print(f"Match Score:    {result['match_score']}/100")
    print(f"Visa Adjusted:  {result['visa_adjusted_score']}/100")
    print(f"Decision:       {result['decision']}")
    print(f"Matched Skills: {result['matched_skills']}")
    print(f"Missing Skills: {result['missing_skills']}")
    print("Reasoning:")
    for reason in result["reasoning"]:
        print(f"  {reason}")
