import os
import sqlite3
import streamlit as st

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
    st.header("🔧 Verifying Pre-requisites Files")

    cwd = os.getcwd()
    st.write(f"Current Directory: `{cwd}`")
    prereq_file = "prerequisites.txt"
    if os.path.exists(prereq_file):
        st.info(f"Checking files listed in `{prereq_file}`...")
        with open(prereq_file, "r") as f:
            for line in f:
                file_name = line.strip()
                if file_name:
                    if os.path.exists(file_name):
                        st.success(f"✅ File found: {file_name}")
                    else:
                        st.error(f"❌ File missing: {file_name}")
    else:
        st.warning(f"Prerequisites file `{prereq_file}` not found.")

    db.connect()
    # Check if any Admin exists
    select_query = "SELECT * FROM users WHERE role = ?"
    params = ("Admin".lower(),)
    admin_users = db.fetch_data(select_query, params)

    if admin_users:
        st.success("✅ Admin user(s) found in the database.")
        if st.button("Show Admin details"):
            st.table(admin_users)
    else:
        # Form to create Admin user
        st.markdown("---")
        st.header("➕ Create Admin User")
        with st.form("add_admin_form"):
            admin_name = st.text_input("Admin Name")
            admin_password = st.text_input("Admin Password", type="password")
            admin_email = st.text_input("Admin Email")
            submit = st.form_submit_button("Create Admin User")

            if submit:
                if not admin_name or not admin_password or not admin_email:
                    st.error("All fields are required!", icon="🚨")
                else:
                    query = "INSERT INTO users (name, email, role, password, verified) VALUES (?, ?, ?, ?, ?)"
                    insert_params = (admin_name, admin_email, "Admin", admin_password, 1)
                    result = db.insert_data(query, insert_params)
                    st.success(f"Admin user '{admin_name}' added successfully.")
                    st.info(result)


# -----------------------------
# Global DB instance
# -----------------------------
db = LocalSQLiteDatabase("local_database.db")

# Run Streamlit setup UI
if __name__ == "__main__":
    run_db_setup()
