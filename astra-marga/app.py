import json
import os
import tempfile
from pathlib import Path

import requests
import gspread
import streamlit as st


def check_ollama_status() -> bool:
    try:
        response = requests.get("http://localhost:11434", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

from modules.job_parser import parse_job
from modules.job_scorer import score_job
from modules.outreach_drafter import draft_outreach
from modules.resume_parser import parse_resume, save_profile
from modules.resume_tailor import tailor_resume
from modules.sheets_tracker import SheetsTracker, get_analytics, log_to_sheets
from modules.visa_detector import analyze_visa_language

st.set_page_config(
    page_title="AI Job Copilot",
    page_icon="💼",
    layout="wide",
)

st.sidebar.title("Astra Marga")
page = st.sidebar.radio("Navigate", ["Upload Resume", "Analyze Job", "📊 Analytics"])

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
            st.subheader("✉️ Outreach Messages")
            st.caption("Review and send manually — nothing is auto-sent.")
            if decision != "Skip":
                if st.button("Generate Outreach Messages"):
                    company = parsed["company"]
                    role = parsed["title"]
                    with st.spinner("Drafting messages..."):
                        outreach = draft_outreach(
                            company=company,
                            role=role,
                            matched_skills=scoring["matched_skills"],
                            job_text=job_text,
                            use_ai=use_ai,
                        )

                    tab1, tab2, tab3, tab4 = st.tabs(
                        ["👤 Recruiter", "🎓 Alumni", "💼 Hiring Manager", "🔄 Follow Up"]
                    )
                    with tab1:
                        st.text_area(
                            "Recruiter Message",
                            outreach["recruiter_message"],
                            height=180,
                        )
                        st.caption(
                            "Find recruiters by searching: "
                            + outreach["search_suggestions"][0]
                        )
                    with tab2:
                        st.text_area("Alumni Message", outreach["alumni_message"], height=180)
                        st.caption(
                            "Find alumni by searching: "
                            + outreach["search_suggestions"][2]
                        )
                    with tab3:
                        st.text_area(
                            "Hiring Manager Message",
                            outreach["hiring_manager_message"],
                            height=180,
                        )
                        st.caption(
                            "Find hiring managers by searching: "
                            + outreach["search_suggestions"][3]
                        )
                    with tab4:
                        st.text_area(
                            "Follow Up Message",
                            outreach["follow_up_message"],
                            height=150,
                        )
                        st.caption("Send this 1 week after applying if no response.")

                    st.subheader("🔍 LinkedIn Search Suggestions")
                    st.caption("Use these searches to find the right people to message.")
                    for suggestion in outreach["search_suggestions"]:
                        st.code(suggestion)

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

            st.divider()
            st.subheader("📋 Add to Tracker")
            col_url, col_source = st.columns(2)
            with col_url:
                job_url = st.text_input(
                    "Job URL (optional)",
                    placeholder="https://linkedin.com/jobs/...",
                )
            with col_source:
                source = st.selectbox(
                    "Where did you find this?",
                    ["LinkedIn", "Handshake", "Glassdoor", "Indeed",
                     "Company Site", "Referral", "Other"],
                )
            notes = st.text_input(
                "Notes (optional)",
                placeholder="Referral, recruiter contact, or follow-up notes",
            )
            if st.button("➕ Add to Tracker"):
                try:
                    log_to_sheets(parsed, result, scoring, job_url, source, notes)
                except (ValueError, FileNotFoundError, gspread.exceptions.APIError) as error:
                    st.error(f"Could not add job to tracker: {error}")
                else:
                    st.success("✅ Added to Google Sheets tracker!")

elif page == "📊 Analytics":
    st.title("📊 Application Analytics")
    st.caption("Insights from your job search")
    try:
        analytics = get_analytics()
    except (ValueError, FileNotFoundError, gspread.exceptions.APIError) as error:
        st.error(f"Could not load Google Sheets analytics: {error}")
    else:
        if not analytics:
            st.info("No applications tracked yet. Analyze a job and add it to the tracker first.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Analyzed", analytics["total"])
            col2.metric("Apply", analytics["apply_count"])
            col3.metric("Maybe", analytics["maybe_count"])
            col4.metric("Skipped", analytics["skip_count"])

            st.divider()
            col5, col6 = st.columns(2)
            with col5:
                st.subheader("Visa Risk Breakdown")
                for risk, count in analytics["visa_risks"].items():
                    st.write(f"**{risk}:** {count} jobs")
            with col6:
                st.subheader("Top Missing Skills")
                for skill, count in analytics["top_missing_skills"]:
                    st.write(f"**{skill}:** missing in {count} jobs")

            st.divider()
            st.subheader("All Applications")
            records = SheetsTracker().get_all_applications()
            if records:
                import pandas as pd
                st.dataframe(pd.DataFrame(records), use_container_width=True)