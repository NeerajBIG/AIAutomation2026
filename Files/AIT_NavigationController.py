import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))
import streamlit as st
import pytz
from datetime import datetime
import time
from dateutil import parser
from streamlit_js_eval import streamlit_js_eval
from AIT_HomepageController import show_homepageQA, show_homepageAdmin
from AIT_LoginController import sessionTime


def parse_sqlite_datetime(dt_str, local_timezone):
    if dt_str is None or dt_str == "":
        return datetime.now(local_timezone)

    try:
        dt = parser.isoparse(dt_str)  # Handles timezone offsets automatically
    except Exception:
        dt = datetime.now(local_timezone)

    # Localize naive datetime
    if dt.tzinfo is None:
        dt = local_timezone.localize(dt)
    return dt


def navigationGuest():
    global minutes_difference, current_datetime, GetSessionTime
    st.sidebar.title("Navigation")
    from AIT_DBConnector import db
    db.connect()
    GetSessionTime = sessionTime()

    local_timezone = pytz.timezone('US/Eastern')
    current_datetime = datetime.now(local_timezone)

    select_query = "SELECT * FROM SessionDetails"
    try:
        resultSessionTable = db.fetch_data(select_query)
        if resultSessionTable is None:
            st.error("Error: Unable to connect with Database, please refresh the browser and try again...")
        elif isinstance(resultSessionTable, list) and len(resultSessionTable) == 0:
            st.warning("Warning: Query succeeded but returned no data.")
        else:
            db.close()
            for record in resultSessionTable:
                session_user = record['userid']
                session_active = record['SessionActive']
                session_time = parse_sqlite_datetime(record['SessionTime'], local_timezone)

                if session_active == 1 and session_user != 1:
                    time_difference = current_datetime - session_time
                    minutes_difference = time_difference.total_seconds() / 60
                    if minutes_difference > GetSessionTime:
                        db.connect()
                        update_query = "UPDATE SessionDetails SET SessionActive = ? WHERE userid = ?"
                        update_params = ('0', session_user)
                        db.update_data(update_query, update_params)
                        db.close()

    except Exception as e:
        st.error(f"Database connection error. Please refresh the browser and try again.")

    page = st.sidebar.radio("Choose a page", ["Home", "Signup", "Login"])
    if page == "Home":
        from AIT_HomepageController import show_homepageGuest
        show_homepageGuest()
    elif page == "Signup":
        from AIT_SignupController import signup
        signup()
    elif page == "Login":
        from AIT_LoginController import login
        login()


def sidebar_navigationQA():
    minutes_difference = 0
    current_datetime = None
    GetSessionTime = sessionTime()

    from AIT_MainApp import controllerFun
    cookie_controller = controllerFun()
    from AIT_DBConnector import db
    db.connect()

    select_query = "SELECT * FROM SessionDetails WHERE userid = ?"
    try:
        local_timezone = pytz.timezone('US/Eastern')
        current_datetime = datetime.now(local_timezone)

        params = (cookie_controller.get('user_id'),)
        resultSessionTable = db.fetch_data(select_query, params)

        if resultSessionTable:
            session_time = parse_sqlite_datetime(resultSessionTable[0]['SessionTime'], local_timezone)
            time_difference = current_datetime - session_time
            minutes_difference = time_difference.total_seconds() / 60

    except Exception:
        pass

    st.sidebar.markdown(f"""
        <div style="background-color: #4CAF50; color: white; padding: 1px 10px; border-radius: 8px; text-align: center; width: 180px; margin: auto;">
        <h5 style="margin: 10; font-size: 14px;">Active since {minutes_difference:.2f} minutes</h5>
        </div>
        """, unsafe_allow_html=True)

    st.sidebar.title("NavigationQA")
    page = st.sidebar.radio("Choose a page",
                            ["Home", "Locator Extractor", "BDD to Code"])
    if page == "Home":
        show_homepageQA()
    elif page == "Locator Extractor":
        from AIT_ElementLocator import run_app
        run_app()
    elif page == "BDD to Code":
        st.write("Pending")

    # Logout logic
    if st.sidebar.button("Logout") or minutes_difference > GetSessionTime:
        update_query = "UPDATE SessionDetails SET SessionActive = ?, SessionTime = ? WHERE userid = ?"
        update_params = ('0', current_datetime, cookie_controller.get('user_id'))
        db.update_data(update_query, update_params)
        db.close()

        # Clear cookies
        cookie_controller.set('role_user', "Guest")
        cookie_controller.set('user_name', "Unknown")
        cookie_controller.set('user_id', "Unknown")
        for cookie in ["cookie_name", "cookie_name1", "user_cookie", "user_role"]:
            try:
                cookie_controller.remove(cookie)
            except:
                pass
        st.sidebar.success("You have been logged out!")
        time.sleep(2)
        streamlit_js_eval(js_expressions="parent.window.location.reload()")


def sidebar_navigationAdmin():
    global minutes_difference, current_datetime, GetSessionTime
    st.sidebar.title("Navigation")
    from AIT_MainApp import controllerFun
    cookie_controller = controllerFun()
    from AIT_DBConnector import db
    db.connect()
    GetSessionTime = sessionTime()

    local_timezone = pytz.timezone('US/Eastern')
    current_datetime = datetime.now(local_timezone)
    select_query = "SELECT * FROM SessionDetails WHERE userid = ?"
    params = (cookie_controller.get('user_id'),)
    resultSessionTable = db.fetch_data(select_query, params)
    session_time = parse_sqlite_datetime(resultSessionTable[0]['SessionTime'], local_timezone)
    time_difference = current_datetime - session_time
    minutes_difference = time_difference.total_seconds() / 60

    st.sidebar.markdown(f"""
    <div style="background-color: #4CAF50; color: white; padding: 1px 10px; border-radius: 8px; text-align: center; width: 180px; margin: auto;">
    <h5 style="margin: 10; font-size: 14px;">Active since {minutes_difference:.2f} minutes</h5>
    </div>
    """, unsafe_allow_html=True)

    page = st.sidebar.radio("Choose a page", ["Home", "DB Access"])
    if page == "Home":
        show_homepageAdmin()
    elif page == "DB Access":
        from AIT_DBAdmin import run_sqlite_admin_portal
        run_sqlite_admin_portal()

    if st.sidebar.button("Logout") or minutes_difference > GetSessionTime:
        update_query = "UPDATE SessionDetails SET SessionActive = ?, SessionTime = ? WHERE userid = ?"
        update_params = ('0', current_datetime, cookie_controller.get('user_id'))
        db.update_data(update_query, update_params)
        db.close()

        # Clear cookies
        cookie_controller.set('role_user', "Guest")
        cookie_controller.set('user_name', "Unknown")
        cookie_controller.set('user_id', "Unknown")
        for cookie in ["cookie_name", "cookie_name1", "user_cookie", "user_role"]:
            try:
                cookie_controller.remove(cookie)
            except:
                pass
        st.sidebar.success("You have been logged out!")
        time.sleep(2)
        streamlit_js_eval(js_expressions="parent.window.location.reload()")
