import streamlit as st
from modules.job_parser import parse_job
from modules.visa_detector import analyze_visa_language

st.set_page_config(
    page_title="AI Job Copilot",
    page_icon="💼",
    layout="wide"
)

st.title("AI Job Copilot")
st.caption("Visa-aware job analyzer for international students")

job_text = st.text_area(
    "Paste job description here",
    height=350,
    placeholder="Paste the full job description..."
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