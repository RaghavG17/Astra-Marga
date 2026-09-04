import os
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Date", "Company", "Role", "Location", "Source", "Job URL",
    "Match Score", "Visa Score", "Visa Risk", "Decision", "Matched Skills",
    "Missing Skills", "Experience Level Fit", "Status", "Resume Version",
    "Outreach Sent", "Follow Up Date", "Notes",
]


def set_column_widths(worksheet: Any) -> None:
    """Sets readable widths for each tracker column."""
    try:
        widths = [
            100, 140, 180, 130, 100, 200, 110, 100, 100,
            100, 200, 200, 130, 110, 120, 120, 120, 250,
        ]
        requests_body = {
            "requests": [
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": worksheet.id,
                            "dimension": "COLUMNS",
                            "startIndex": index,
                            "endIndex": index + 1,
                        },
                        "properties": {"pixelSize": width},
                        "fields": "pixelSize",
                    }
                }
                for index, width in enumerate(widths)
            ]
        }
        worksheet.spreadsheet.batch_update(requests_body)
    except Exception as error:
        print(f"Column width error: {error}")


class SheetsTracker:
    """Logs analyzed jobs and reads application analytics from Google Sheets."""

    def __init__(self) -> None:
        self.sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not self.sheet_id:
            raise ValueError("GOOGLE_SHEET_ID is not configured.")

        credentials_path = Path(__file__).resolve().parent.parent / "credentials.json"
        if not credentials_path.exists():
            raise FileNotFoundError(f"Google credentials not found: {credentials_path}")

        credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES,
        )
        self.client = gspread.authorize(credentials)
        spreadsheet = self.client.open_by_key(self.sheet_id)

        try:
            self.sheet = spreadsheet.worksheet("Applications")
        except gspread.WorksheetNotFound:
            self.sheet = spreadsheet.add_worksheet(
                title="Applications",
                rows=1000,
                cols=len(HEADERS),
            )
            self.sheet.append_row(HEADERS)
            self._format_header(self.sheet)

        if not self.sheet.row_values(1):
            self.sheet.append_row(HEADERS)
            self._format_header(self.sheet)

    def _format_header(self, worksheet: Any) -> None:
        """Makes the header row bold, colored, and frozen by column group."""
        try:
            worksheet.freeze(rows=1)
            color_ranges = {
                "A1:F1": {"red": 0.267, "green": 0.447, "blue": 0.769},
                "G1:H1": {"red": 0.204, "green": 0.596, "blue": 0.329},
                "I1:I1": {"red": 0.851, "green": 0.451, "blue": 0.122},
                "J1:J1": {"red": 0.459, "green": 0.267, "blue": 0.694},
                "K1:L1": {"red": 0.118, "green": 0.565, "blue": 0.565},
                "M1:N1": {"red": 0.184, "green": 0.459, "blue": 0.271},
                "O1:P1": {"red": 0.239, "green": 0.349, "blue": 0.608},
                "Q1:R1": {"red": 0.4, "green": 0.4, "blue": 0.4},
            }
            header_format = {
                "textFormat": {
                    "bold": True,
                    "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    "fontSize": 10,
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "wrapStrategy": "CLIP",
            }
            for cell_range, color in color_ranges.items():
                worksheet.format(
                    cell_range,
                    {**header_format, "backgroundColor": color},
                )
            set_column_widths(worksheet)
        except Exception as error:
            print(f"Formatting error: {error}")


    def log_job(
        self,
        parsed_job: dict[str, Any],
        visa_result: dict[str, Any],
        scoring_result: dict[str, Any],
        job_url: str = "",
        source: str = "Manual",
        notes: str = "",
    ) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        row = [
            today,
            parsed_job.get("company", "Unknown"),
            parsed_job.get("title", "Unknown"),
            parsed_job.get("location", "Unknown"),
            source,
            job_url,
            f"{scoring_result.get('match_score', 0)}/100",
            f"{visa_result.get('score', 0)}/100",
            visa_result.get("risk_level", "Unknown"),
            scoring_result.get("decision", "Unknown"),
            ", ".join(scoring_result.get("matched_skills", [])[:5]),
            ", ".join(scoring_result.get("missing_skills", [])[:5]),
            scoring_result.get("experience_level_fit", ""),
            "Found",
            "v1",
            "No",
            today,
            notes,
        ]
        self.sheet.append_row(row)

    def get_all_applications(self) -> list[dict[str, Any]]:
        return self.sheet.get_all_records()

    def get_analytics(self) -> dict[str, Any]:
        records = self.get_all_applications()
        if not records:
            return {}

        decisions: dict[str, int] = {}
        visa_risks: dict[str, int] = {}
        missing_skills: dict[str, int] = {}
        for record in records:
            decision = record.get("Decision", "Unknown")
            decisions[decision] = decisions.get(decision, 0) + 1
            risk = record.get("Visa Risk", "Unknown")
            visa_risks[risk] = visa_risks.get(risk, 0) + 1
            for skill in str(record.get("Missing Skills", "")).split(","):
                skill = skill.strip()
                if skill:
                    missing_skills[skill] = missing_skills.get(skill, 0) + 1

        return {
            "total": len(records),
            "decisions": decisions,
            "visa_risks": visa_risks,
            "top_missing_skills": sorted(
                missing_skills.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:5],
            "apply_count": decisions.get("Apply", 0),
            "maybe_count": decisions.get("Maybe", 0),
            "skip_count": decisions.get("Skip", 0),
        }


def log_to_sheets(
    parsed_job: dict[str, Any],
    visa_result: dict[str, Any],
    scoring_result: dict[str, Any],
    job_url: str = "",
    source: str = "Manual",
    notes: str = "",
) -> None:
    SheetsTracker().log_job(
        parsed_job, visa_result, scoring_result, job_url, source, notes
    )


def get_analytics() -> dict[str, Any]:
    return SheetsTracker().get_analytics()
