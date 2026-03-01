import os
import sqlite3
import streamlit as st
import streamlit.components.v1 as components

class LocalSQLiteDatabase:
    def __init__(self, db_path="local_database.db"):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        db_exists = os.path.exists(self.db_path)
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row

            if not db_exists:
                st.info("No Database found — creating new DB and required tables...")
                self.create_tables()

        except Exception as e:
            st.error(f"Error connecting to DB: {e}")

    # Close SQLite connection
    def close(self):
        if self.connection:
            self.connection.close()
            #st.info("Connection closed,,.")

    # Auto-create necessary tables
    def create_tables(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT UNIQUE,
                    role TEXT,
                    password TEXT,
                    verified INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SessionDetails (
                    userid INTEGER PRIMARY KEY AUTOINCREMENT,
                    SessionActive INTEGER,
                    SessionTime DATETIME
                    ButtonColor TEXT
                )
            """)
            self.connection.commit()
            cursor.close()
            st.success("Required tables created successfully.")
        except Exception as e:
            st.error(f"Error creating tables: {e}")

    # Execute SELECT query
    def execute_query(self, query, params=None):
        if not self.connection:
            st.error("❌ No active connection. Call connect() first.")
            return None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or [])
            rows = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in rows]
        except Exception as e:
            st.error(f"Error: {e}")
            return None

    # Execute INSERT / UPDATE / DELETE
    def execute_update(self, query, params=None):
        if not self.connection:
            st.error("❌ No active connection. Call connect() first.")
            return None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or [])
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return f"Query executed successfully. {affected} row(s) affected."
        except Exception as e:
            self.connection.rollback()
            return f"Error: {e}"

    # Wrappers
    def fetch_data(self, query, params=None):
        return self.execute_query(query, params)

    def insert_data(self, query, params=None):
        return self.execute_update(query, params)

    def update_data(self, query, params=None):
        return self.execute_update(query, params)

    def delete_data(self, query, params=None):
        return self.execute_update(query, params)


def run_db_setup():
    st.header("Verifying Pre-requisites Files")

    # Initialize session state for Check button
    if "check_clicked" not in st.session_state:
        st.session_state.check_clicked = False
        st.session_state.cwd = ""
        st.session_state.prereq_results = []

    # Check button logic
    if st.button("Check"):
        st.session_state.check_clicked = True
        st.session_state.cwd = os.getcwd()
        prereq_file = "prerequisites.txt"
        prereq_results = []

        if os.path.exists(prereq_file):
            prereq_results.append(("info", f"Checking required files."))
            with open(prereq_file, "r") as f:
                for line in f:
                    file_name = line.strip()
                    if file_name:
                        if os.path.exists(file_name):
                            prereq_results.append(("success", f"✅ File found: {file_name}"))
                        else:
                            prereq_results.append(("error", f"❌ File missing: {file_name}"))
        else:
            prereq_results.append(("warning", f"Prerequisites file `{prereq_file}` not found."))

        st.session_state.prereq_results = prereq_results

    # Display Check results if clicked
    if st.session_state.check_clicked:
        st.write(f"Current Directory: `{st.session_state.cwd}`")
        for status, message in st.session_state.prereq_results:
            if status == "info":
                st.info(message)
            elif status == "success":
                st.success(message)
            elif status == "error":
                st.error(message)
            elif status == "warning":
                st.warning(message)

        # Database check
        db.connect()
        select_query = "SELECT name, email FROM users WHERE role = ?"
        params = ("admin",)
        admin_users = db.fetch_data(select_query, params)

        if admin_users:
            st.success("✅ Admin user(s) found in the database.")
            if st.button("Show Admin details"):
                st.table(admin_users)
        else:
            # Form to create Admin user
            st.markdown("---")
            st.error("❌ No Admin user found in the database.")
            st.header("➕ Create Admin User")
            with st.form("add_admin_form"):
                admin_name = st.text_input("Admin Name")
                admin_password = st.text_input("Admin Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                admin_email = st.text_input("Admin Email")
                submit = st.form_submit_button("Create Admin User")

                if submit:
                    if not admin_name or not admin_password or not admin_email:
                        st.error("All fields are required!", icon="🚨")
                    elif admin_password != confirm_password:
                        st.error("❌ Password and Confirm Password do not match.")
                    else:
                        query = "INSERT INTO users (name, email, role, password, verified) VALUES (?, ?, ?, ?, ?)"
                        insert_params = (admin_name, admin_email, "admin", admin_password, 1)
                        result = db.insert_data(query, insert_params)
                        st.success(f"Admin user '{admin_name}' created successfully. Please refresh and login")
                        st.warning(
                            "🔐 Please copy and store this password in a safe location. It will not be shown again.")

                        components.html(f"""
                            <div style="display:flex; align-items:center; gap:10px;">
                                <input type="text" value="{admin_password}" id="passwordField"
                                    style="padding:8px; width:260px; border-radius:6px; border:1px solid #ccc;" readonly>

                                <button onclick="
                                    navigator.clipboard.writeText(document.getElementById('passwordField').value);
                                    document.getElementById('copyMsg').innerHTML='✅ Password copied successfully!';
                                "
                                style="
                                    padding:8px 14px;
                                    border:none;
                                    border-radius:6px;
                                    background-color:#4CAF50;
                                    color:white;
                                    cursor:pointer;
                                    font-weight:600;
                                ">
                                    📋 Copy Password
                                </button>
                            </div>

                            <div id="copyMsg" style="margin-top:8px; color:green; font-weight:400;"></div>
                            """, height=90)

db = LocalSQLiteDatabase("local_database.db")

if __name__ == "__main__":
    run_db_setup()
