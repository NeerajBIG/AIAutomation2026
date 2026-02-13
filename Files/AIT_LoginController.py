import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))
import streamlit as st
import pytz
from datetime import datetime, timedelta
import time

def sessionTime():
    SessionTime = 60
    return SessionTime

def controllerFun():
    from streamlit_cookies_controller import CookieController
    controller = CookieController()
    return controller

def login():
    cookie_controller = controllerFun()
    st.title("Login")
    email = st.text_input("Enter your Email")
    password = st.text_input("Enter your Password", type="password")

    if st.button("Login"):
        if not email or not password:
            st.error("All fields are required!", icon="🚨")
        else:
            select_query = "SELECT * FROM users WHERE email = ?"
            from AIT_DBConnector import db
            db.connect()
            try:
                params = (email,)
                result = db.fetch_data(select_query, params)
                # st.write(db.fetch_data(select_query, params))
                # st.write(result)

                email = email.lower()

                if len(result) == 0:
                    st.error("Login failed! Unknown username or password.", icon="🚨")

                elif result[0]['email'] == email and result[0]['verified'] == 0:
                    st.error(f"Hi, {result[0]['name']}! You account is pending approval and is not yet active for login.")

                elif result[0]['email'] == email and result[0]['verified'] == 1 and result[0]['password'] != password:
                    st.error("Login failed! Invalid username or password.", icon="🚨")

                elif result[0]['email'] == email and result[0]['verified'] == 2 and result[0]['password'] == password:
                    st.error("Account Disabled", icon="🚨")

                elif result[0]['email'] == email and result[0]['verified'] == 1 and result[0]['password'] == password:
                    st.success(f"Login successful! Welcome back, {result[0]['name']}!")

                    local_timezone = pytz.timezone('US/Eastern')
                    current_datetime = datetime.now(local_timezone)

                    check_query = "SELECT COUNT(*) FROM SessionDetails WHERE userid = ?"
                    check_params = (result[0]['id'],)
                    record_exists = db.fetch_data(check_query, check_params)

                    if str(record_exists) == "[{'COUNT(*)': 0}]":
                        insert_query = "INSERT INTO SessionDetails (userid, SessionActive, SessionTime) VALUES (?, ?, ?)"
                        insert_params = (result[0]['id'], '1', current_datetime)
                        db.insert_data(insert_query, insert_params)

                    else:
                        update_query = """
                        UPDATE SessionDetails 
                        SET SessionActive = ?, SessionTime = ? 
                        WHERE userid = ?
                        """
                        update_params = ('1', current_datetime, result[0]['id'])
                        db.update_data(update_query, update_params)

                    expires = datetime.now() + timedelta(days=365 * 10)
                    status_placeholder = st.empty()

                    time.sleep(1)
                    cookie_controller.set('role_user', result[0]['role'], expires=expires)
                    status_placeholder.write("Saving your session....")

                    time.sleep(1)
                    cookie_controller.set('user_name', result[0]['name'], expires=expires)
                    status_placeholder.write("Loading your profile....")

                    time.sleep(1)
                    cookie_controller.set('user_id', result[0]['id'], expires=expires)
                    status_placeholder.write("All set, redirecting to your profile....")

                    time.sleep(1)
                    st.rerun()

                db.close()

            except Exception as e:
                st.error(f"Database connection error. Please refresh the browser and try again.")