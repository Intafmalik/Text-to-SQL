"""
ui.py
-----
Streamlit interface for the Text-to-SQL agent.

Run with:
    streamlit run app/ui.py
"""

from __future__ import annotations

import csv
import io

import streamlit as st

from app.agent import run_question
from app.database import get_table_names, test_connection


EXAMPLE_QUESTIONS = [
    "How many customers do we have in each country?",
    "What are the top 5 best-selling products by revenue?",
    "Which employees report to the VP of Sales?",
    "What is the total payment amount received from each customer in 2004?",
    "List all orders that are currently on hold.",
]


def initialize_state() -> None:
    """Create Streamlit session-state keys used by the UI."""
    if "question" not in st.session_state:
        st.session_state.question = EXAMPLE_QUESTIONS[0]
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_output" not in st.session_state:
        st.session_state.last_output = None


def set_question(question: str) -> None:
    """Set the active question from an example/history button."""
    st.session_state.question = question


def render_styles() -> None:
    """Small visual polish while keeping the app native to Streamlit."""
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1180px;
                padding-top: 2rem;
                padding-bottom: 3rem;
            }
            .status-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                padding: 0.35rem 0.65rem;
                border: 1px solid rgba(49, 51, 63, 0.18);
                border-radius: 0.45rem;
                font-size: 0.88rem;
                font-weight: 600;
                background: rgba(250, 250, 250, 0.75);
            }
            .metric-row {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.75rem;
                margin: 0.75rem 0 1rem;
            }
            .metric-card {
                border: 1px solid rgba(49, 51, 63, 0.14);
                border-radius: 0.5rem;
                padding: 0.75rem 0.85rem;
                background: rgba(255, 255, 255, 0.65);
            }
            .metric-label {
                color: rgba(49, 51, 63, 0.68);
                font-size: 0.78rem;
                margin-bottom: 0.2rem;
            }
            .metric-value {
                color: rgb(31, 41, 55);
                font-size: 1.25rem;
                font-weight: 700;
            }
            @media (max-width: 760px) {
                .metric-row {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Sidebar with database context and reusable question shortcuts."""
    with st.sidebar:
        st.subheader("Database")
        db_ok = test_connection()
        pill_text = "Connected" if db_ok else "Not connected"
        pill_color = "#15803d" if db_ok else "#b91c1c"
        st.markdown(
            f"<span class='status-pill' style='color: {pill_color};'>{pill_text}</span>",
            unsafe_allow_html=True,
        )

        st.caption("ClassicModels PostgreSQL")
        st.write(", ".join(get_table_names()))

        st.divider()
        st.subheader("Examples")
        for index, question in enumerate(EXAMPLE_QUESTIONS, start=1):
            st.button(
                question,
                key=f"example_{index}",
                use_container_width=True,
                on_click=set_question,
                args=(question,),
            )

        if st.session_state.history:
            st.divider()
            st.subheader("Recent")
            for index, item in enumerate(st.session_state.history[:5], start=1):
                st.button(
                    item["question"],
                    key=f"history_{index}",
                    use_container_width=True,
                    on_click=set_question,
                    args=(item["question"],),
                )


def render_output(output: dict) -> None:
    """Render one agent response."""
    if output["success"]:
        st.success("Query completed")
    else:
        st.error("Query failed")

    row_count = len(output.get("results") or [])
    st.markdown(
        f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">Rows</div>
                <div class="metric-value">{row_count}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Attempts</div>
                <div class="metric-value">{output["attempts"]}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Latency</div>
                <div class="metric-value">{output["latency_s"]}s</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if output.get("nl_answer"):
        st.subheader("Answer")
        st.write(output["nl_answer"])

    st.subheader("Generated SQL")
    st.code(output.get("sql") or "", language="sql")

    if output.get("error"):
        st.subheader("Error")
        st.error(output["error"])

    st.subheader("Results")
    if output.get("results"):
        rows = output["results"]
        st.dataframe(rows, use_container_width=True, hide_index=True)

        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        st.download_button(
            "Download CSV",
            data=csv_buffer.getvalue().encode("utf-8"),
            file_name="text2sql_results.csv",
            mime="text/csv",
            use_container_width=False,
        )
    elif output["success"]:
        st.info("The query ran successfully but returned no rows.")


def main() -> None:
    st.set_page_config(
        page_title="Text-to-SQL Agent",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_state()
    render_styles()
    render_sidebar()

    st.title("Text-to-SQL Agent")
    st.caption("Ask questions about the ClassicModels database and inspect the generated SQL.")

    with st.form("question_form"):
        question = st.text_area(
            "Question",
            key="question",
            height=100,
            placeholder="Example: Which customers have the highest total payments?",
        )

        left, right = st.columns([1, 4])
        with left:
            submitted = st.form_submit_button("Run Query", use_container_width=True)
        with right:
            verbose = st.checkbox("Verbose logs", value=False)

    if submitted:
        cleaned_question = question.strip()
        if not cleaned_question:
            st.warning("Enter a question before running the agent.")
            return

        with st.spinner("Generating SQL, executing it, and preparing the answer..."):
            output = run_question(cleaned_question, verbose=verbose)

        st.session_state.last_output = output
        st.session_state.history = [
            {"question": cleaned_question, "success": output["success"]},
            *[
                item
                for item in st.session_state.history
                if item["question"] != cleaned_question
            ],
        ][:8]

    if st.session_state.last_output:
        st.divider()
        render_output(st.session_state.last_output)


if __name__ == "__main__":
    main()
