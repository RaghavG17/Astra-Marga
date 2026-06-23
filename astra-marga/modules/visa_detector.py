import re
from dataclasses import dataclass, asdict
from typing import List, Dict


@dataclass
class VisaDetectionResult:
    risk_level: str
    recommendation: str
    red_flags: List[str]
    positive_signals: List[str]
    unclear_signals: List[str]
    score: int


class VisaDetector:
    """
    Rule-based visa and sponsorship language detector.

    This module does not give legal advice.
    It only detects language in job descriptions that may indicate
    whether a role is friendly, unclear, or risky for OPT / future sponsorship.
    """

    HARD_REJECTION_PATTERNS = [
        r"we do not sponsor",
        r"does not sponsor",
        r"no sponsorship",
        r"unable to sponsor",
        r"cannot sponsor",
        r"will not sponsor",
        r"without sponsorship now or in the future",
        r"without employer sponsorship",
        r"must not require sponsorship",
        r"must be authorized to work.*without.*sponsorship",
        r"permanent work authorization",
        r"u\.s\. citizens? only",
        r"green card holders? only",
        r"security clearance required",
        r"must have.*security clearance",
    ]

    OPT_NEGATIVE_PATTERNS = [
        r"no opt",
        r"no cpt",
        r"opt candidates.*not eligible",
        r"cpt candidates.*not eligible",
        r"students on opt.*not eligible",
        r"f-1.*not eligible",
    ]

    POSITIVE_PATTERNS = [
        r"visa sponsorship.*available",
        r"sponsorship.*available",
        r"will sponsor",
        r"open to sponsorship",
        r"h-1b sponsorship",
        r"h1b sponsorship",
        r"opt",
        r"cpt",
        r"stem opt",
        r"e-verify",
        r"international students",
    ]

    UNCLEAR_PATTERNS = [
        r"must be authorized to work in the united states",
        r"authorized to work in the u\.s\.",
        r"work authorization required",
        r"employment eligibility",
        r"legally authorized to work",
    ]

    def __init__(self) -> None:
        self.hard_rejection_patterns = [re.compile(p, re.I) for p in self.HARD_REJECTION_PATTERNS]
        self.opt_negative_patterns = [re.compile(p, re.I) for p in self.OPT_NEGATIVE_PATTERNS]
        self.positive_patterns = [re.compile(p, re.I) for p in self.POSITIVE_PATTERNS]
        self.unclear_patterns = [re.compile(p, re.I) for p in self.UNCLEAR_PATTERNS]

    def _find_matches(self, text: str, patterns: List[re.Pattern]) -> List[str]:
        matches = []
        for pattern in patterns:
            found = pattern.search(text)
            if found:
                matches.append(found.group(0))
        return list(dict.fromkeys(matches))

    def detect(self, job_text: str) -> VisaDetectionResult:
        normalized_text = " ".join(job_text.lower().split())

        hard_red_flags = self._find_matches(normalized_text, self.hard_rejection_patterns)
        opt_red_flags = self._find_matches(normalized_text, self.opt_negative_patterns)
        positive_signals = self._find_matches(normalized_text, self.positive_patterns)
        unclear_signals = self._find_matches(normalized_text, self.unclear_patterns)

        red_flags = hard_red_flags + opt_red_flags

        if red_flags:
            return VisaDetectionResult(
                risk_level="High",
                recommendation="Skip or manually verify before spending time applying.",
                red_flags=red_flags,
                positive_signals=positive_signals,
                unclear_signals=unclear_signals,
                score=20,
            )

        if positive_signals and not red_flags:
            return VisaDetectionResult(
                risk_level="Low",
                recommendation="Likely worth applying, but still verify details on the application form.",
                red_flags=[],
                positive_signals=positive_signals,
                unclear_signals=unclear_signals,
                score=85,
            )

        if unclear_signals:
            return VisaDetectionResult(
                risk_level="Medium",
                recommendation="Maybe apply. The posting is unclear, so verify during the application.",
                red_flags=[],
                positive_signals=[],
                unclear_signals=unclear_signals,
                score=55,
            )

        return VisaDetectionResult(
            risk_level="Unknown",
            recommendation="No clear visa-related language found. Treat as unknown and check company history later.",
            red_flags=[],
            positive_signals=[],
            unclear_signals=[],
            score=50,
        )


def analyze_visa_language(job_text: str) -> Dict:
    detector = VisaDetector()
    result = detector.detect(job_text)
    return asdict(result)


if __name__ == "__main__":
    sample_job = """
    Candidates must be legally authorized to work in the United States.
    We are unable to sponsor now or in the future.
    """

    result = analyze_visa_language(sample_job)
    print(result)