import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))
import streamlit as st
from captcha.image import ImageCaptcha
import random
import string
from io import BytesIO
import time
import re


# db = MySQLDatabase(
#     host='sql5.freesqldatabase.com',
#     user='sql5801118',
#     password='mqgWHRyzR1',
#     database='sql5801118'
# )

def generate_captcha_text(length=6):
    characters = string.digits
    return ''.join(random.choices(characters, k=length))

def generate_captcha_image(text):
    image_captcha = ImageCaptcha(width=280, height=90, font_sizes=(60,))
    image = image_captcha.generate_image(text)
    return image

# Signup logic
def addUser():
    st.title("Create New User")

    name = st.text_input("Enter Name")
    email = st.text_input("Enter Email (Unique accepted only)")
    role = st.selectbox("Select Role", ['Select', 'QA', 'Admin'])
    password = st.text_input("Enter your Password", type="password")
    confirm_password = st.text_input("Confirm your Password", type="password")

    if 'captcha_text' not in st.session_state or 'captcha_image' not in st.session_state or st.button("Reload CAPTCHA"):
        st.session_state.captcha_text = generate_captcha_text()
        st.session_state.captcha_image = generate_captcha_image(st.session_state.captcha_text)
        st.session_state.captcha_input = ''

    captcha_image = st.session_state.captcha_image
    captcha_bytes = BytesIO()
    captcha_image.save(captcha_bytes, format='PNG')
    captcha_bytes.seek(0)
    st.image(captcha_bytes, caption='CAPTCHA Image', use_container_width=True)

    user_input = st.text_input('Enter the CAPTCHA text:', key='captcha_input')

    email = email.lower()

    if user_input:
        time.sleep(2)
        if user_input == st.session_state.captcha_text:
            st.success('CAPTCHA verification successful!')

            if st.button("Submit"):
                if not name or not email or not password or not confirm_password or role == "Select":
                    st.error("All fields are required!", icon="🚨")
                elif bool(re.search(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$", email)) != True:
                    st.error("Invalid email address", icon="🚨")
                elif password != confirm_password:
                    st.error("Passwords do not match.", icon="🚨")
                else:
                    from DBConnector import db
                    db.connect()

                    select_query = "SELECT * FROM users WHERE email = ?"
                    params = (email,)
                    result = db.fetch_data(select_query, params)
                    time.sleep(2)
                    if not result:
                        insert_query = "INSERT INTO users (name, email, role, password, verified) VALUES (?, ?, ?, ?, ?)"
                        insert_params = (name, email, role, confirm_password, '1')
                        db.insert_data(insert_query, insert_params)
                        st.text("Please wait")
                        time.sleep(3)

                        select_query = "SELECT * FROM users WHERE email = ?"
                        params = (email,)
                        result = db.fetch_data(select_query, params)

                        if len(result) == 0:
                            st.error("Signup failed! Please try again.", icon="🚨")
                        elif len(result) == 1:
                            st.success(
                                f"User added successful! User should use email '{result[0]['email']}' and set password to login.")
                    else:
                        st.error("This email address is already registered.", icon="🚨")
                    db.close()
                    time.sleep(3)
                    st.rerun()
        else:
            st.error('CAPTCHA verification failed. Try again.')
