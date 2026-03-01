import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))
import time
import streamlit as st
from NavigationController import sidebar_navigationQA, navigationGuest, sidebar_navigationAdmin


def controllerFun():
    from streamlit_cookies_controller import CookieController
    controller = CookieController()
    return controller

def main():
    cookie_controller = controllerFun()
    cookie = cookie_controller.get('role_user')
    if str(cookie) == "None":
        cookie1 = cookie_controller.get('role_user')
        time.sleep(3)
        if str(cookie1) == "None":
            cookie_controller.set('role_user', "Guest")
            cookie_controller.set('user_name', "Unknown")
            cookie_controller.set('user_id', "Unknown")

    from DBConnector import db
    db.connect()
    select_query = """
                        SELECT ButtonColor 
                        FROM SessionDetails 
                        WHERE userid = ?
                    """
    result = db.fetch_data(select_query, (cookie_controller.get('user_id'),))
    db.close()

    if not result:
        result = [{'ButtonColor': '#ea6c0b'}]

    if (cookie_controller.get('role_user')).lower() == 'Guest'.lower():
        st.markdown(f"""
                <style>
                div.stButton > button:first-child {{
                    background-color: {result[0]["ButtonColor"]};
                    color: white;
                }}
                </style>
            """, unsafe_allow_html=True)

        navigationGuest()

    elif (cookie_controller.get('role_user')).lower() == 'QA'.lower():
        color = "#ea6c0b"
        st.markdown(f"""
                <style>
                div.stButton > button:first-child {{
                    background-color: {result[0]["ButtonColor"]};
                    color: white;
                }}
                </style>
            """, unsafe_allow_html=True)
        sidebar_navigationQA()
    elif (cookie_controller.get('role_user')).lower() == 'Admin'.lower():
        color = "#ea6c0b"
        st.markdown(f"""
                <style>
                div.stButton > button:first-child {{
                    background-color: {result[0]["ButtonColor"]};
                    color: white;
                }}
                </style>
            """, unsafe_allow_html=True)
        sidebar_navigationAdmin()

if __name__ == '__main__':
    main()
