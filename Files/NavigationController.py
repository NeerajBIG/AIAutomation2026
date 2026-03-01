import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))
import streamlit as st
import pytz
from datetime import datetime
import time
from dateutil import parser
from streamlit_js_eval import streamlit_js_eval
from HomepageController import show_homepageQA, show_homepageAdmin
from LoginController import sessionTime


def parse_sqlite_datetime(dt_str, local_timezone):
    if dt_str is None or dt_str == "":
        return datetime.now(local_timezone)

    try:
        dt = parser.isoparse(dt_str)
    except Exception:
        dt = datetime.now(local_timezone)

    if dt.tzinfo is None:
        dt = local_timezone.localize(dt)
    return dt


def navigationGuest():
    global minutes_difference, current_datetime, GetSessionTime
    st.sidebar.title("Navigation")
    from DBConnector import db
    db.connect()
    GetSessionTime = sessionTime()
    session_user = 0

    local_timezone = pytz.timezone('US/Eastern')
    current_datetime = datetime.now(local_timezone)

    select_query = "SELECT * FROM SessionDetails"
    try:
        resultSessionTable = db.fetch_data(select_query)
        #st.text(resultSessionTable)
        if resultSessionTable is None:
            st.error("Error: Unable to connect with Database, please refresh the browser and try again...")
        elif isinstance(resultSessionTable, list) and len(resultSessionTable) == 0:
            pass
            #st.error("Warning: Query succeeded but returned no data.")
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

    page = st.sidebar.radio("Choose a page", ["Home", "Login"])

    if page == "Home":
        from HomepageController import show_homepageGuest
        show_homepageGuest()

    #--- Signup code hidden
    # elif page == "Signup":
    #     from SignupController import signup
    #     signup()

    elif page == "Login":
        from LoginController import login
        login()


def sidebar_navigationQA():
    minutes_difference = 0
    current_datetime = None
    GetSessionTime = sessionTime()

    from MainApp import controllerFun
    cookie_controller = controllerFun()
    from DBConnector import db
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
        <div style="background-color: #4CAF50; color: white; padding: 1px 10px; border-radius: 8px; text-align: center; width: 180px; margin: 10px auto 10px auto;">
        <h5 style="margin: 10; font-size: 14px;">Active since {minutes_difference:.2f} minutes</h5>
        </div>
        """, unsafe_allow_html=True)

    result = db.fetch_data(select_query, (cookie_controller.get('user_id'),))
    db.close()
    if not result:
        result = [{'ButtonColor': '#ea6c0b'}]
    if st.sidebar.button("Logout") or minutes_difference > GetSessionTime:
        st.markdown(f"""
                                <style>
                                div.stButton > button:first-child {{
                                    background-color: {result[0]["ButtonColor"]};
                                    color: white;
                                }}
                                </style>
                            """, unsafe_allow_html=True)
        update_query = "UPDATE SessionDetails SET SessionActive = ?, SessionTime = ? WHERE userid = ?"
        update_params = ('0', current_datetime, cookie_controller.get('user_id'))
        db.update_data(update_query, update_params)
        db.close()

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

    st.sidebar.title("Navigation Panel")
    page = st.sidebar.radio("Choose a page",
                            ["Home", "Locator Extractor", "BDD to Code"])

    color = st.sidebar.color_picker("Change buttons color?", "#ea6c0b")
    result = db.fetch_data(select_query, (cookie_controller.get('user_id'),))
    db.close()
    if not result:
        result = [{'ButtonColor': '#ea6c0b'}]
    if st.sidebar.button("Save Button Color"):
        st.markdown(f"""
                        <style>
                        div.stButton > button:first-child {{
                            background-color: {result[0]["ButtonColor"]};
                            color: white;
                        }}
                        </style>
                    """, unsafe_allow_html=True)
        try:
            db.connect()
            update_query = """
                        UPDATE SessionDetails 
                        SET ButtonColor = ?
                        WHERE userid = ?
                    """
            update_params = (
                color,
                cookie_controller.get('user_id')
            )
            db.update_data(update_query, update_params)
            db.close()
            st.sidebar.success("Button color saved successfully!")
            time.sleep(2)
            streamlit_js_eval(js_expressions="parent.window.location.reload()")

        except Exception as e:
            st.sidebar.error(f"Error saving color: {e}")

    if page == "Home":
        show_homepageQA()
    elif page == "Locator Extractor":
        from ElementLocator import run_app
        run_app()
    elif page == "BDD to Code":
        from BDDToCode import run_app
        run_app()


def sidebar_navigationAdmin():
    global minutes_difference, current_datetime, GetSessionTime
    st.sidebar.title("Navigation")

    from MainApp import controllerFun
    cookie_controller = controllerFun()
    # st.text(cookie_controller.get('user_name'))
    # st.text(cookie_controller.get('user_id'))
    # st.text(cookie_controller.get('role_user'))

    from DBConnector import db
    db.connect()
    GetSessionTime = sessionTime()

    local_timezone = pytz.timezone('US/Eastern')
    current_datetime = datetime.now(local_timezone)

    select_query = "SELECT * FROM SessionDetails WHERE userid = ?"
    params = (cookie_controller.get('user_id'),)
    resultSessionTable = db.fetch_data(select_query, params)

    #----Added condition if user's Session data got lost in SessionTable, set cookie_controller data as GUEST user.
    if isinstance(resultSessionTable, list) and len(resultSessionTable) == 0:
        cookie_controller.set('role_user', "Guest")
        cookie_controller.set('user_name', "Unknown")
        cookie_controller.set('user_id', "Unknown")

    session_time = parse_sqlite_datetime(resultSessionTable[0]['SessionTime'], local_timezone)
    time_difference = current_datetime - session_time
    minutes_difference = time_difference.total_seconds() / 60

    st.sidebar.markdown(f"""
    <div style="background-color: #4CAF50; color: white; padding: 1px 10px; border-radius: 8px; text-align: center; width: 180px; margin: 10px auto 10px auto;">
    <h5 style="margin: 10; font-size: 14px;">Active since {minutes_difference:.2f} minutes</h5>
    </div>
    """, unsafe_allow_html=True)

    result = db.fetch_data(select_query, (cookie_controller.get('user_id'),))
    db.close()
    if not result:
        result = [{'ButtonColor': '#ea6c0b'}]
    if st.sidebar.button("Logout") or minutes_difference > GetSessionTime:
        st.markdown(f"""
                                <style>
                                div.stButton > button:first-child {{
                                    background-color: {result[0]["ButtonColor"]};
                                    color: white;
                                }}
                                </style>
                            """, unsafe_allow_html=True)
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

    page = st.sidebar.radio("Choose a page", ["Home", "Add Users", "DB Access"])

    color = st.sidebar.color_picker("Change buttons color?", "#ea6c0b")
    result = db.fetch_data(select_query, (cookie_controller.get('user_id'),))
    db.close()
    if not result:
        result = [{'ButtonColor': '#ea6c0b'}]
    if st.sidebar.button("Save Button Color"):
        st.markdown(f"""
                                <style>
                                div.stButton > button:first-child {{
                                    background-color: {result[0]["ButtonColor"]};
                                    color: white;
                                }}
                                </style>
                            """, unsafe_allow_html=True)
        try:
            db.connect()
            update_query = """
                    UPDATE SessionDetails 
                    SET ButtonColor = ?
                    WHERE userid = ?
                """
            update_params = (
                color,
                cookie_controller.get('user_id')
            )
            db.update_data(update_query, update_params)
            db.close()
            st.sidebar.success("Button color saved successfully!")
            time.sleep(2)
            streamlit_js_eval(js_expressions="parent.window.location.reload()")

        except Exception as e:
            st.sidebar.error(f"Error saving color: {e}")

    if page == "Home":
        show_homepageAdmin()
    elif page == "Add Users":
        from AddUsersController import addUser
        addUser()
    elif page == "DB Access":
        from DBAdmin import run_sqlite_admin_portal
        run_sqlite_admin_portal()