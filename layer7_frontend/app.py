"""Module 7.1: Interactive Streamlit Frontend for SE Best Practices Assistant."""

import os
import requests
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="SE Best Practices Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished look
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .finding-card {
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #E2E8F0;
        background-color: #F8FAFC;
    }
    .badge-high {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-medium {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-low {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Sidebar Configuration
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Python-Dark.svg",
        width=48,
    )
    # Retrieve API URL from st.secrets, os.environ, or fallback
    default_api_url = "http://localhost:8000"
    if hasattr(st, "secrets"):
        default_api_url = st.secrets.get("API_BASE_URL", st.secrets.get("API_BASE", default_api_url))
    if default_api_url == "http://localhost:8000":
        default_api_url = os.environ.get("API_BASE_URL", os.environ.get("API_BASE", default_api_url))

    api_base_input = st.text_input(
        "FastAPI Backend URL",
        value=default_api_url,
        help="Endpoint where layer6_api is running.",
    )
    api_base = api_base_input.strip().rstrip("/")

    # Health check
    try:
        health_resp = requests.get(f"{api_base}/health", timeout=5.0)
        if health_resp.status_code == 200:
            st.success("🟢 API Connected", icon="✅")
        else:
            st.warning(f"🟡 API responded with status {health_resp.status_code}")
    except Exception as e:
        st.error(f"🔴 API Offline\nCould not connect to `{api_base}`\n({e})")


    st.markdown("---")
    st.markdown("### 📚 Evaluation Scope")
    st.markdown(
        """
    - **SOLID Principles** (SRP, OCP, LSP, ISP, DIP)
    - **OWASP Top 10 Security** (Injection, Broken Auth)
    - **Clean Code & PEP 8** (Complexity, Naming)
    - **Static Analysis** (Bandit, AST, Radon)
    """
    )


# Header
st.markdown('<div class="main-header">🛡️ SE Best Practices Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Agentic code review grounded in software engineering knowledge bases and static analysis tools.</div>',
    unsafe_allow_html=True,
)

# Input Section
col_upload, col_paste = st.columns([1, 1])

with col_upload:
    uploaded_file = st.file_uploader("Upload Python source file", type=["py"])

with col_paste:
    code_pasted = st.text_area(
        "Or paste Python code here",
        height=180,
        placeholder="def process_order(user_id, total):\n    db.execute(f'SELECT * FROM orders WHERE user={user_id}')\n    ...",
    )

# Determine active code
code_to_review = ""
if uploaded_file is not None:
    code_to_review = uploaded_file.getvalue().decode("utf-8", errors="replace")
elif code_pasted and code_pasted.strip():
    code_to_review = code_pasted

# Review Action Button
if st.button("🚀 Run Agentic Review", type="primary", use_container_width=True):
    if not code_to_review.strip():
        st.warning("Please provide a Python code snippet or upload a .py file.")
    else:
        with st.spinner("Analyzing code with Agent Graph (Planner ➔ Retriever ➔ Tools ➔ Analyzer ➔ Reflection)..."):
            try:
                response = requests.post(
                    f"{api_base}/review",
                    json={"code": code_to_review},
                    timeout=60,
                )
                if response.status_code == 200:
                    data = response.json()
                    session_id = response.headers.get("X-Session-Id", "default-session")
                    st.session_state["findings"] = data.get("findings", [])
                    st.session_state["report_markdown"] = data.get("report_markdown", "")
                    st.session_state["iteration_count"] = data.get("iteration_count", 1)
                    st.session_state["session_id"] = session_id
                    st.session_state["reviewed_code"] = code_to_review
                    st.session_state["decisions"] = {}
                    st.success("Review complete!")
                else:
                    detail = response.json().get("detail", "Unknown server error")
                    st.error(f"Review failed (HTTP {response.status_code}): {detail}")
            except requests.exceptions.ConnectionError:
                st.error("Backend API is unreachable. Please start the server with `uvicorn layer6_api.main:app --port 8000`.")
            except Exception as exc:
                st.error(f"Error during review request: {exc}")

# Display Results Dashboard
if "findings" in st.session_state and st.session_state["findings"] is not None:
    findings = st.session_state["findings"]
    session_id = st.session_state.get("session_id", "session")
    iter_count = st.session_state.get("iteration_count", 1)

    n_high = sum(1 for f in findings if f.get("severity", "").lower() == "high")
    n_med = sum(1 for f in findings if f.get("severity", "").lower() == "medium")
    n_low = sum(1 for f in findings if f.get("severity", "").lower() == "low")
    n_total = len(findings)

    # Metrics Summary Row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Findings", n_total)
    m2.metric("High Severity", n_high, delta=None if n_high == 0 else f"{n_high} critical", delta_color="inverse")
    m3.metric("Medium Severity", n_med)
    m4.metric("Low Severity", n_low)
    m5.metric("Agent Iterations", iter_count)

    st.markdown("---")

    # Tabs for structured viewing
    tab_findings, tab_report, tab_source = st.tabs(
        ["🔍 Interactive Findings & HITL Decisions", "📑 Full Markdown Report", "💻 Source Code"]
    )

    with tab_findings:
        if not findings:
            st.info("🎉 No best practice violations detected! Code adheres to all evaluated standards.")
        else:
            for idx, f in enumerate(findings):
                sev = f.get("severity", "medium").lower()
                sev_icon = "🔴" if sev == "high" else ("🟡" if sev == "medium" else "🟢")
                badge_class = f"badge-{sev}"
                principle = f.get("principle", "General Practice")
                location = f.get("location", "code")
                explanation = f.get("explanation", "")
                fix = f.get("suggested_fix", "")
                cid = f.get("evidence_chunk_id", "")

                decision_status = st.session_state.get("decisions", {}).get(idx, None)

                with st.container(border=True):
                    # Title line with badge
                    c_title, c_status = st.columns([3, 1])
                    with c_title:
                        st.markdown(
                            f"### {sev_icon} **{principle}** — `{location}`",
                        )
                    with c_status:
                        if decision_status == "accept":
                            st.success("Accepted ✅")
                        elif decision_status == "reject":
                            st.error("Rejected ❌")
                        elif decision_status == "edit":
                            st.info("Edited 📝")

                    # Description & Fix
                    st.write(explanation)

                    st.markdown("**Suggested Refactoring / Fix:**")
                    st.code(fix, language="python")

                    # Source Citation
                    if cid.startswith("tool:"):
                        st.caption(f"🔧 **Evidence Source:** Static Analysis Tool (`{cid}`)")
                    elif cid and cid != "none":
                        st.caption(f"📖 **Evidence Source:** Knowledge Base Chunk (`{cid}`)")
                    else:
                        st.caption("ℹ️ **Evidence Source:** Zero-Shot Standard Practice")

                    # Decision Controls
                    c_acc, c_rej, c_edit = st.columns([1, 1, 2])

                    if c_acc.button("✅ Accept", key=f"btn_accept_{idx}"):
                        try:
                            requests.post(
                                f"{api_base}/review/{session_id}/decision",
                                json={"finding_index": idx, "decision": "accept"},
                                timeout=5,
                            )
                            st.session_state["decisions"][idx] = "accept"
                            st.toast(f"Finding #{idx+1} Accepted!", icon="✅")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Failed to record decision: {exc}")

                    if c_rej.button("❌ Reject", key=f"btn_reject_{idx}"):
                        try:
                            requests.post(
                                f"{api_base}/review/{session_id}/decision",
                                json={"finding_index": idx, "decision": "reject"},
                                timeout=5,
                            )
                            st.session_state["decisions"][idx] = "reject"
                            st.toast(f"Finding #{idx+1} Rejected!", icon="❌")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Failed to record decision: {exc}")

                    edit_key = f"editing_mode_{idx}"
                    if c_edit.button("✏️ Edit Suggested Fix", key=f"btn_toggle_edit_{idx}"):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                        st.rerun()

                    # Collapsible / active edit box
                    if st.session_state.get(edit_key, False):
                        edited_val = st.text_area(
                            f"Modify fix for Finding #{idx+1}:",
                            value=fix,
                            key=f"edit_text_area_{idx}",
                        )
                        if st.button("💾 Save & Submit Edited Fix", key=f"btn_save_edit_{idx}"):
                            try:
                                requests.post(
                                    f"{api_base}/review/{session_id}/decision",
                                    json={
                                        "finding_index": idx,
                                        "decision": "edit",
                                        "edited_text": edited_val,
                                    },
                                    timeout=5,
                                )
                                st.session_state["decisions"][idx] = "edit"
                                st.session_state[edit_key] = False
                                st.toast(f"Finding #{idx+1} Updated with custom fix!", icon="📝")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Failed to record edit: {exc}")

    with tab_report:
        report_md = st.session_state.get("report_markdown", "")
        st.markdown(report_md)
        st.download_button(
            label="📥 Download Review Report (Markdown)",
            data=report_md,
            file_name="code_review_report.md",
            mime="text/markdown",
        )

    with tab_source:
        reviewed_code = st.session_state.get("reviewed_code", "")
        st.code(reviewed_code, language="python", line_numbers=True)
