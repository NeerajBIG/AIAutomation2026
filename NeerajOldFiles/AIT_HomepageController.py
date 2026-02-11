import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))
import streamlit as st
from AIT_DBConnector import run_db_setup


def show_homepageGuest():
    from AIT_MainApp import controllerFun
    cookie_controller = controllerFun()
    text = "BIG Automation Tool"
    num_chars = len(text)
    flashing_html = "".join([
        f'<span class="flashing-text">{char}</span>' if char != " " else '<span class="flashing-text">&nbsp;</span>'
        for char in text
    ])
    animation_delays = "\n".join(
        [f".flashing-text:nth-child({i + 1}) {{ animation-delay: {i * 0.2}s; }}" for i in range(num_chars)])

    st.markdown(f"""
            <style>
                .flashing-text {{
                    font-size: 60px;
                    font-weight: none;
                    color: navy;  
                    display: inline-block;
                    opacity: 1;
                    animation: flash 1s forwards;
                }}

                {animation_delays}

                @keyframes flash {{
                    0% {{ opacity: 1; }}
                    50% {{ opacity: 0; }}
                    100% {{ opacity: 1; }}
                }}
            </style>
        """, unsafe_allow_html=True)
    st.markdown(f'<p>{flashing_html}</p>', unsafe_allow_html=True)

    st.title(f"Hi, {cookie_controller.get('role_user')}!")
    st.write(f"Sign up to unlock all features, or log in if you already have an account.")

    run_db_setup()

def show_homepageQA():
    from AIT_MainApp import controllerFun
    cookie_controller = controllerFun()
    text = "BIG Automation Tool"
    num_chars = len(text)
    flashing_html = "".join([
        f'<span class="flashing-text">{char}</span>' if char != " " else '<span class="flashing-text">&nbsp;</span>'
        for char in text
    ])
    animation_delays = "\n".join(
        [f".flashing-text:nth-child({i + 1}) {{ animation-delay: {i * 0.2}s; }}" for i in range(num_chars)])

    st.markdown(f"""
            <style>
                .flashing-text {{
                    font-size: 60px;
                    font-weight: none;
                    color: navy;  
                    display: inline-block;
                    opacity: 1;
                    animation: flash 1s forwards;
                }}

                {animation_delays}

                @keyframes flash {{
                    0% {{ opacity: 1; }}
                    50% {{ opacity: 0; }}
                    100% {{ opacity: 1; }}
                }}
            </style>
        """, unsafe_allow_html=True)
    st.markdown(f'<p>{flashing_html}</p>', unsafe_allow_html=True)

    if cookie_controller.get('role_user') == "QA":
        st.title(f"Welcome, {cookie_controller.get('user_name')}!")
        st.write(f"Your Role: {cookie_controller.get('role_user')}")

    else:
        st.write("You need to log in first!")

def show_homepageAdmin():
    from AIT_MainApp import controllerFun
    cookie_controller = controllerFun()
    text = "BIG Automation Tool"
    num_chars = len(text)
    flashing_html = "".join([
        f'<span class="flashing-text">{char}</span>' if char != " " else '<span class="flashing-text">&nbsp;</span>'
        for char in text
    ])
    animation_delays = "\n".join(
        [f".flashing-text:nth-child({i + 1}) {{ animation-delay: {i * 0.2}s; }}" for i in range(num_chars)])

    st.markdown(f"""
            <style>
                .flashing-text {{
                    font-size: 60px;
                    font-weight: none;
                    color: navy;  
                    display: inline-block;
                    opacity: 1;
                    animation: flash 1s forwards;
                }}

                {animation_delays}

                @keyframes flash {{
                    0% {{ opacity: 1; }}
                    50% {{ opacity: 0; }}
                    100% {{ opacity: 1; }}
                }}
            </style>
        """, unsafe_allow_html=True)
    st.markdown(f'<p>{flashing_html}</p>', unsafe_allow_html=True)

    if cookie_controller.get('role_user') == "Admin":
        st.title(f"Welcome, {cookie_controller.get('user_name')}!")
        st.write(f"Your Role: {cookie_controller.get('role_user')}")
    else:
        st.write("You need to log in first!")