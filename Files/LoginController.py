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

    clicked_button = None
    col1, col2 = st.columns(2)

    from DBConnector import db
    db.connect()
    with col1:
        if st.button("Login"):
            if not email or not password:
                clicked_button = "FieldsRequired"
            else:
                select_query = "SELECT * FROM users WHERE email = ?"

                try:
                    params = (email,)
                    result = db.fetch_data(select_query, params)
                    # st.write(db.fetch_data(select_query, params))
                    # st.write(result)

                    email = email.lower()

                    if len(result) == 0:
                        clicked_button = "UnknownUsername"

                    elif result[0]['email'] == email and result[0]['verified'] == 0:
                        clicked_button = "AccountPending"

                    elif result[0]['email'] == email and result[0]['verified'] == 1 and result[0]['password'] != password:
                        clicked_button = "InvalidUorP"

                    elif result[0]['email'] == email and result[0]['verified'] == 2 and result[0]['password'] == password:
                        clicked_button = "AccountDisabled"

                    elif result[0]['email'] == email and result[0]['verified'] == 1 and result[0]['password'] == password:
                        clicked_button = "LoginSuccessful"

                except Exception as e:
                    st.error(f"Database connection error. Please refresh the browser and try again.")

    with col2:
        if st.button("Forgot Password?"):
            clicked_button = "ForgotPassword"

    if clicked_button == "ForgotPassword":
        st.info("Please contact with your Admin user to retrieve your password.")
    if clicked_button == "FieldsRequired":
        st.error("All fields are required!", icon="🚨")
    if clicked_button == "UnknownUsername":
        st.error("Login failed! Unknown username or password.", icon="🚨")
    if clicked_button == "AccountPending":
        st.error(f"Hi, {result[0]['name']}! You account is pending approval and is not yet active for login.")
    if clicked_button == "InvalidUorP":
        st.error("Login failed! Invalid username or password.", icon="🚨")
    if clicked_button == "AccountDisabled":
        st.error("Account Disabled", icon="🚨")
    if clicked_button == "LoginSuccessful":
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

        db.close()
        time.sleep(1)
        st.rerun()

