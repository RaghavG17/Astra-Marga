import os
import tempfile
from pathlib import Path

import streamlit as st

from modules.job_parser import parse_job
from modules.resume_parser import parse_resume, save_profile
from modules.visa_detector import analyze_visa_language

st.set_page_config(
    page_title="AI Job Copilot",
    page_icon="💼",
    layout="wide",
)

st.sidebar.title("Astra Marga")
page = st.sidebar.radio("Navigate", ["Upload Resume", "Analyze Job"])

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
            st.write("**Strong**")
            st.write(", ".join(sorted(all_strong)) or "None")
        with col2:
            st.write("**Medium**")
            st.write(", ".join(sorted(all_medium)) or "None")
        with col3:
            st.write("**Beginner**")
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
            st.subheader("Job Details")
            parsed = parse_job(job_text)

            col3, col4 = st.columns(2)
            with col3:
                st.write("**Title:**", parsed["title"])
                st.write("**Company:**", parsed["company"])
                st.write("**Location:**", parsed["location"])
                st.write("**Level:**", parsed["experience_level"])
            with col4:
                st.write("**Skills Found:**")
                for skill in parsed["required_skills"]:
                    st.badge(skill)