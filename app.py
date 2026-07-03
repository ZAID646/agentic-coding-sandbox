import streamlit as st
from src.main import run_sandbox


st.set_page_config(
    page_title="Agentic Coding Sandbox",
    page_icon=":zap:",
    layout="wide",
)

st.title("Self-Correcting Agentic Coding Sandbox")
st.markdown(
    "Submit a coding task. The system generates, executes, and autonomously debugs "
    "Python code in an isolated sandbox environment."
)

with st.sidebar:
    st.header("About")
    st.markdown(
        """
**Architecture:**
1. **Coder Agent** - generates Python code via LLM
2. **Sandbox Executor** - runs code in isolated environment
3. **Critic Agent** - analyzes errors and suggests fixes
4. **Retry Loop** - up to 3 self-healing attempts
"""
    )
    st.caption("Running on Hugging Face Spaces")

col1, col2 = st.columns([3, 2])

with col1:
    prompt = st.text_area(
        "Describe what you want the code to do:",
        height=150,
        placeholder="e.g., Plot a bar chart of the top 5 most frequent words in this text.",
    )

    if st.button("Run", type="primary", disabled=not prompt):
        with st.spinner("Generating code..."):
            try:
                result = run_sandbox(prompt)
                st.session_state["result"] = result
            except Exception as e:
                st.error(f"Error: {e}")

with col2:
    st.subheader("Result")

    if "result" in st.session_state:
        result = st.session_state["result"]
        retries = result.get("retries_used", 0)

        if result.get("success"):
            st.success(f"Succeeded ({retries} retries)")
        else:
            st.error(f"Failed ({retries} retries)")

        files = result.get("files", {})
        if files:
            for name, b64 in files.items():
                st.image(f"data:image/png;base64,{b64}", caption=name, use_container_width=True)

        output = result.get("output") or result.get("error") or "No output"
        if output.strip():
            st.code(output, language="text", line_numbers=True)
    else:
        st.info("Submit a prompt to see results here.")

st.divider()

st.subheader("Execution Trace")

if "result" in st.session_state:
    trace = st.session_state["result"].get("trace", [])
    if trace:
        for i, entry in enumerate(trace):
            node = entry.get("node", "?")
            retry = entry.get("retry", 0)

            with st.expander(f"Attempt {retry + 1} - {node}", expanded=True):
                st.json(entry)
    else:
        st.caption("No trace data available.")
else:
    st.caption("Run a prompt to see the execution trace.")
