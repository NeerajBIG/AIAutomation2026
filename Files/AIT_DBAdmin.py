import os
import streamlit as st
import sqlite3
import pandas as pd
import openai
from dotenv import load_dotenv


def run_sqlite_admin_portal():
    DB_PATH = "local_database.db"

    # Streamlit page config
    st.set_page_config(page_title="SQLite Admin Portal", layout="wide")
    st.title("🗄️ SQLite Admin Portal")
    st.markdown(f"**Database:** `{DB_PATH}`")

    # Load OpenAI API key
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY_NEW")
    if not api_key:
        st.error("OpenAI API key not found. Please check your .env file.")
        st.stop()
    openai.api_key = api_key
    client = openai

    # -------------------------
    # SQLite helpers
    # -------------------------
    def quote_ident(name: str) -> str:
        safe = name.replace('"', '""')
        return f'"{safe}"'

    def get_connection():
        if not os.path.exists(DB_PATH):
            return None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception:
            return None

    def list_tables(conn):
        q = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        return [r["name"] for r in conn.execute(q).fetchall()]

    def read_table(conn, table):
        return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)

    import re

    def is_safe_sql(query: str) -> (bool, str):
        """
        Returns (True, "") if safe, otherwise (False, reason)
        """
        q = query.strip().lower()

        # Block multiple statements
        if ";" in q.rstrip(";"):
            return False, "Multiple SQL statements are not allowed."

        blocked_keywords = [
            r"\balter\b",
            r"\bdrop\b",
            r"\bcreate\b",
            r"\brename\b",
            r"\btruncate\b",
            r"\bvaccum\b",
            r"\battach\b",
            r"\bdetach\b",
            r"\breplace\b",
            r"\bindex\b"
        ]

        blocked_writes = [
            r"\binsert\b",
            r"\bupdate\b",
            r"\bdelete\b"
        ]

        patterns = blocked_keywords + blocked_writes

        for pattern in patterns:
            if re.search(pattern, q):
                clean_keyword = pattern.replace("\\b", "")
                return False, f"This query is blocked for safety: contains `{clean_keyword}`"

        if not q.startswith("select") and not q.startswith("with"):
            return False, "Only SELECT queries are allowed in Manual SQL Console."

        return True, ""

    def execute_sql(conn, sql: str):
        try:
            cur = conn.cursor()
            cur.execute(sql)
            conn.commit()
            if cur.description:  # SELECT query
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                return pd.DataFrame(rows, columns=cols), None
            return None, f"Query executed successfully, {cur.rowcount} row(s) affected."
        except Exception as e:
            return None, str(e)

    # -------------------------
    # OpenAI: English → SQL
    # -------------------------
    def generate_sql_from_english(question: str, tables: dict) -> str:
        """
        Generate SQLite SQL from English using OpenAI Chat API
        """
        schema_desc = "\n".join([f"Table `{t}` has columns: {', '.join(cols)}" for t, cols in tables.items()])

        system_prompt = f"""
        You are an expert in SQLite SQL queries.
        You know the following database schema:
        
        {schema_desc}
        
        Instructions:
        - Translate the user request into a proper SQLite SQL query.
        - Only generate queries based on the tables and columns listed above.
        - If the user asks something outside of this database context, reply only:
        "Sorry, I can't help in this context"
        - Provide only the SQL query without explanation.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0,
                max_tokens=300
            )
            sql_query = response.choices[0].message.content.strip()
            # Clean any leading/trailing quotes/backticks
            sql_query = sql_query.strip('`').strip("'").strip('"')
            return sql_query
        except Exception as e:
            return f"-- Error generating SQL: {e}"

    # -------------------------
    # Connect to DB
    # -------------------------
    conn = get_connection()
    if not conn:
        st.error("❌ Local Database not found")
        st.stop()

    tables = list_tables(conn)
    if not tables:
        st.warning("⚠ No tables found in the database.")
        st.stop()

    # Build table schema dictionary for OpenAI
    tables_dict = {}
    for t in tables:
        cols_info = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
        tables_dict[t] = [c[1] for c in cols_info]  # column names

    # -------------------------
    # Table view with refresh
    # -------------------------
    selected_table = st.selectbox("Select a table to view:", tables)

    if st.button("🔄 Refresh"):
        st.rerun()
    df = read_table(conn, selected_table)
    st.subheader(f"Table Data: `{selected_table}`")
    st.dataframe(df, height=500, use_container_width=True)

    # -------------------------
    # Manual SQL console
    # -------------------------
    st.markdown("---")
    st.header("💻 SQL Query Console (Manual)")
    sql_query_manual = st.text_area("Enter SQL query:", height=150)
    if st.button("Run SQL"):
        if sql_query_manual.strip() == "":
            st.warning("Please enter a SQL query")
        else:
            is_safe, reason = is_safe_sql(sql_query_manual)
            if not is_safe:
                st.error(f"❌ Unsafe SQL blocked!\n\n**Reason:** {reason}")
            else:
                result_df, message = execute_sql(conn, sql_query_manual)
                if result_df is not None:
                    st.success("✅ Query executed successfully. Result:")
                    st.dataframe(result_df, height=400, use_container_width=True)
                else:
                    st.info(message)

    # -------------------------
    # English → SQL
    # -------------------------
    st.markdown("---")
    st.header("💬 Ask in English (OpenAI → SQL)")
    user_question = st.text_area("Describe your request in plain English", height=100, key="openai_sql")

    if st.button("Generate SQL from English"):
        if not user_question.strip():
            st.warning("Please enter a question")
        else:
            sql_query = generate_sql_from_english(user_question, tables_dict)
            st.subheader("Generated SQL (copy & run in SQL Console above)")
            st.info("Copy this query and paste it into the SQL Query Console to execute.")
            sql_query = sql_query.replace("sql", "")
            sql_query = sql_query.rstrip()
            st.code(sql_query)
