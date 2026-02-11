import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))
import time
import streamlit as st
from AIT_NavigationController import sidebar_navigationQA, navigationGuest, sidebar_navigationAdmin


def controllerFun():
    from streamlit_cookies_controller import CookieController
    controller = CookieController()
    return controller

def main():
    cookie_controller = controllerFun()
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: #ff9559;
            color: white;
        }
        </style>""", unsafe_allow_html=True)

    cookie = cookie_controller.get('role_user')
    if str(cookie) == "None":
        cookie1 = cookie_controller.get('role_user')
        time.sleep(3)
        if str(cookie1) == "None":
            cookie_controller.set('role_user', "Guest")
            cookie_controller.set('user_name', "Unknown")
            cookie_controller.set('user_id', "Unknown")

    if (cookie_controller.get('role_user')).lower() == 'Guest'.lower():
        navigationGuest()
    elif (cookie_controller.get('role_user')).lower() == 'QA'.lower():
        sidebar_navigationQA()
    elif (cookie_controller.get('role_user')).lower() == 'Admin'.lower():
        sidebar_navigationAdmin()

if __name__ == '__main__':
    main()
