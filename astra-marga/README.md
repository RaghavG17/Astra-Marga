# Astra Marga 🌟
> AI-powered job search copilot for international students on F-1/OPT

## What it does
- Analyzes job descriptions for visa/sponsorship risk
- Scores job fit against your profile
- Tailors resume bullets using local AI (no data leaves your machine)
- Tracks applications in Google Sheets

## Stack
- Python + Streamlit
- Ollama + llama3.2 (local AI, free)
- spaCy + Regex (NLP)
- Google Sheets API

## Setup
```bash
git clone https://github.com/yourusername/astra-marga
cd astra-marga
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp data/master_profile_sample.json data/master_profile.json
# Edit master_profile.json with your real info
streamlit run app.py
```

## Built by

Raghav Gautam — SJSU Computer Engineering, Fall 2026
