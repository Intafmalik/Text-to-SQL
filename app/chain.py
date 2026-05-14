"""
chain.py
--------
Sets up the LangChain SQL generation chain using Google Gemini.
This is the core chain that converts NL questions → SQL queries.
"""

import os
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.prompts import SQL_GENERATION_SYSTEM_PROMPT, SQL_CORRECTION_PROMPT, NL_ANSWER_PROMPT
from app.database import get_schema_description

load_dotenv()


# ─────────────────────────────────────────────
# 1. LLM setup
# ─────────────────────────────────────────────

def get_llm(temperature: float = None) -> ChatGoogleGenerativeAI:
    """
    Returns a configured Gemini LLM instance.
    
    Uses gemini-1.5-flash by default (free tier, fast).
    Change GEMINI_MODEL in .env to 'gemini-1.5-pro' for better accuracy.
    """
    api_key    = os.getenv("GOOGLE_API_KEY")
    model      = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    temp       = temperature if temperature is not None else float(os.getenv("TEMPERATURE", "0.1"))
    
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not set. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temp,
        convert_system_message_to_human=True,  # Gemini quirk
    )


# ─────────────────────────────────────────────
# 2. SQL generation chain
# ─────────────────────────────────────────────

def get_sql_generation_chain():
    """
    Returns a LangChain chain:
      question → SQL string
    
    Chain structure:
      PromptTemplate → Gemini LLM → StrOutputParser → clean_sql
    """
    llm = get_llm()
    
    prompt = PromptTemplate(
        input_variables=["question", "schema"],
        template=SQL_GENERATION_SYSTEM_PROMPT + "\nQuestion: {question}\n\nSQL:"
    )
    
    chain = (
        {
            "question": RunnablePassthrough(),
            "schema": lambda _: get_schema_description(),
        }
        | prompt
        | llm
        | StrOutputParser()
        | clean_sql
    )
    
    return chain


# ─────────────────────────────────────────────
# 3. SQL correction chain (for retry)
# ─────────────────────────────────────────────

def get_sql_correction_chain():
    """
    Returns a chain for self-correction:
      {question, faulty_sql, error_message} → corrected SQL string
    """
    llm = get_llm(temperature=0.0)  # More deterministic for fixes
    
    prompt = PromptTemplate(
        input_variables=["question", "faulty_sql", "error_message", "schema"],
        template=SQL_CORRECTION_PROMPT
    )
    
    chain = (
        {
            "question":      lambda x: x["question"],
            "faulty_sql":    lambda x: x["faulty_sql"],
            "error_message": lambda x: x["error_message"],
            "schema":        lambda _: get_schema_description(),
        }
        | prompt
        | llm
        | StrOutputParser()
        | clean_sql
    )
    
    return chain


# ─────────────────────────────────────────────
# 4. Natural language answer chain
# ─────────────────────────────────────────────

def get_nl_answer_chain():
    """
    Returns a chain that turns SQL results into a natural language answer:
      {question, results} → natural language string
    """
    llm = get_llm(temperature=0.3)
    
    prompt = PromptTemplate(
        input_variables=["question", "results"],
        template=NL_ANSWER_PROMPT
    )
    
    chain = prompt | llm | StrOutputParser()
    return chain


# ─────────────────────────────────────────────
# 5. Utility: clean LLM SQL output
# ─────────────────────────────────────────────

def clean_sql(raw_output: str) -> str:
    """
    Strips common LLM artifacts from SQL output:
    - Markdown code fences (```sql ... ```)
    - Leading/trailing whitespace
    - "SQL:" prefix
    - Semicolons at end (SQLAlchemy doesn't need them)
    """
    sql = raw_output.strip()
    
    # Remove markdown code fences
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    
    # Remove common prefixes the model sometimes adds
    sql = re.sub(r"^(?:SQL:|Query:|Answer:)\s*", "", sql, flags=re.IGNORECASE)
    
    # Remove trailing semicolons (psycopg2 handles this)
    sql = sql.rstrip(";").strip()
    
    return sql


# ─────────────────────────────────────────────
# 6. Quick test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing SQL generation chain...")
    chain = get_sql_generation_chain()
    
    question = "How many customers are in France?"
    sql = chain.invoke(question)
    
    print(f"Question: {question}")
    print(f"Generated SQL: {sql}")
