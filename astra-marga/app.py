import json
import os
import tempfile
from pathlib import Path

import requests
import streamlit as st


def check_ollama_status() -> bool:
    try:
        response = requests.get("http://localhost:11434", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

from modules.job_parser import parse_job
from modules.job_scorer import score_job
from modules.resume_parser import parse_resume, save_profile
from modules.resume_tailor import tailor_resume
from modules.visa_detector import analyze_visa_language

st.set_page_config(
    page_title="AI Job Copilot",
    page_icon="💼",
    layout="wide",
)

st.sidebar.title("Astra Marga")
page = st.sidebar.radio("Navigate", ["Upload Resume", "Analyze Job"])

st.sidebar.divider()
st.sidebar.subheader("⚙️ Settings")

ollama_running = check_ollama_status()

if ollama_running:
    st.sidebar.success("🟢 Ollama: Online")
else:
    st.sidebar.error("🔴 Ollama: Offline")

use_ai = st.sidebar.toggle(
    "Use AI Tailoring",
    value=ollama_running,
    disabled=not ollama_running,
    help="Requires Ollama running locally. Turn off to save battery.",
)

if not ollama_running:
    st.sidebar.caption("Run `ollama serve` in terminal to enable AI features.")

if page == "Upload Resume":
    st.title("Build Your Profile")
    st.caption("Upload your resume and we'll extract your skills automatically")

    uploaded_files = st.file_uploader(
        "Upload your resume(s)",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        import tempfile
        import os

        all_strong, all_medium, all_beginner = set(), set(), set()
        all_projects, all_experience = [], []
        last_profile = {}

        for uploaded_file in uploaded_files:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=Path(uploaded_file.name).suffix,
            ) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            profile = parse_resume(tmp_path)
            os.unlink(tmp_path)

            if not profile:
                continue

            last_profile = profile
            all_strong.update(profile["skills"]["strong"])
            all_medium.update(profile["skills"]["medium"])
            all_beginner.update(profile["skills"]["beginner"])
            all_projects.extend(profile["projects"])
            all_experience.extend(profile["experience"])

        st.subheader("Skills Extracted")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Strong**")
            st.write(", ".join(sorted(all_strong)) or "None")
        with col2:
            st.markdown("**Medium**")
            st.write(", ".join(sorted(all_medium)) or "None")
        with col3:
            st.markdown("**Beginner**")
            st.write(", ".join(sorted(all_beginner)) or "None")

        st.subheader("Projects Found")
        for p in all_projects:
            with st.expander(p["name"]):
                for b in p["bullets"]:
                    st.write(f"• {b}")

        st.subheader("Experience Found")
        for e in all_experience:
            with st.expander(f"{e['role']} at {e['company']}"):
                for b in e["bullets"]:
                    st.write(f"• {b}")

        if st.button("Save Profile"):
            if not last_profile:
                st.warning("No valid resume data was extracted.")
            else:
                merged = last_profile.copy()
                merged["skills"] = {
                    "strong": list(all_strong),
                    "medium": list(all_medium),
                    "beginner": list(all_beginner),
                }
                merged["projects"] = all_projects
                merged["experience"] = all_experience
                save_profile(merged)
                st.success("Profile saved to data/master_profile.json")

elif page == "Analyze Job":
    st.title("AI Job Copilot")
    st.caption("Visa-aware job analyzer for international students")

    job_text = st.text_area(
        "Paste job description here",
        height=350,
        placeholder="Paste the full job description...",
    )

    if st.button("Analyze Job"):
        if not job_text.strip():
            st.warning("Please paste a job description first.")
        else:
            result = analyze_visa_language(job_text)

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Visa Risk")
                st.metric("Risk Level", result["risk_level"])
                st.metric("Visa Score", result["score"])

            with col2:
                st.subheader("Recommendation")
                st.write(result["recommendation"])

            st.subheader("Detected Red Flags")
            if result["red_flags"]:
                for flag in result["red_flags"]:
                    st.error(flag)
            else:
                st.success("No hard visa red flags detected.")

            st.subheader("Positive Signals")
            if result["positive_signals"]:
                for signal in result["positive_signals"]:
                    st.success(signal)
            else:
                st.info("No positive visa signals detected.")

            st.subheader("Unclear Signals")
            if result["unclear_signals"]:
                for signal in result["unclear_signals"]:
                    st.warning(signal)
            else:
                st.info("No unclear authorization language detected.")

            st.divider()

            scoring = score_job(job_text, result)
            decision = scoring["decision"]
            if decision == "Apply":
                st.success(f"🟢 Decision: {decision}")
            elif decision == "Maybe":
                st.warning(f"🟡 Decision: {decision}")
            else:
                st.error(f"🔴 Decision: {decision}")

            col3, col4 = st.columns(2)
            with col3:
                st.metric("Match Score", f"{scoring['match_score']}/100")
            with col4:
                st.metric("Overall Score", f"{scoring['visa_adjusted_score']}/100")

            st.subheader("Reasoning")
            for reason in scoring["reasoning"]:
                st.write(reason)

            col5, col6 = st.columns(2)
            with col5:
                st.subheader("✅ Matched Skills")
                if scoring["matched_skills"]:
                    st.write(", ".join(scoring["matched_skills"]))
                else:
                    st.write("None matched")
            with col6:
                st.subheader("⚠️ Missing Skills")
                if scoring["missing_skills"]:
                    st.write(", ".join(scoring["missing_skills"]))
                else:
                    st.write("No gaps found")

            st.divider()
            st.subheader("📄 Tailored Resume Bullets")
            if decision != "Skip":
                if use_ai:
                    with st.spinner("Generating tailored bullets using local AI..."):
                        tailoring = tailor_resume(
                            job_text,
                            scoring["matched_skills"],
                            scoring["missing_skills"],
                        )

                    st.write("**Rewritten bullets for this job:**")
                    for bullet in tailoring["tailored_bullets"]:
                        st.write(f"• {bullet}")

                    st.subheader("🔍 Truth Check")
                    for check in tailoring["truth_check"]:
                        st.write(check)

                    if tailoring["omitted_skills"]:
                        st.subheader("⚠️ Skills to Mention in Interview")
                        st.write("In JD but not in your profile — be honest:")
                        st.write(", ".join(tailoring["omitted_skills"]))
                else:
                    st.info("AI tailoring is off. Showing your most relevant original bullets.")
                    profile_path = "data/master_profile.json"
                    if Path(profile_path).exists():
                        with open(profile_path, "r", encoding="utf-8") as file:
                            profile = json.load(file)

                        all_bullets = []
                        for exp in profile.get("experience", []):
                            for bullet in exp.get("bullets", []):
                                all_bullets.append(bullet)
                        for proj in profile.get("projects", []):
                            for bullet in proj.get("bullets", []):
                                all_bullets.append(bullet)

                        job_words = set(job_text.lower().split())
                        ranked = sorted(
                            all_bullets,
                            key=lambda bullet: len(set(bullet.lower().split()) & job_words),
                            reverse=True,
                        )
                        for bullet in ranked[:5]:
                            st.write(f"• {bullet}")
                    else:
                        st.warning("No saved profile found yet. Save a resume first.")
            else:
                st.info("Skipping resume tailoring — job flagged as Skip.")

            st.divider()
            st.subheader("Job Details")
            parsed = parse_job(job_text)

            col7, col8 = st.columns(2)
            with col7:
                st.write("**Title:**", parsed["title"])
                st.write("**Company:**", parsed["company"])
                st.write("**Location:**", parsed["location"])
                st.write("**Level:**", parsed["experience_level"])
            with col8:
                st.write("**Skills Found:**")
                for skill in parsed["required_skills"]:
                    st.badge(skill)