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
def signup():
    st.title("Signup")

    name = st.text_input("Enter your Name")
    email = st.text_input("Enter your Email")
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

            if st.button("Signup"):
                if not name or not email or not password or not confirm_password or role == "Select":
                    st.error("All fields are required!", icon="🚨")
                elif bool(re.search(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$", email)) != True:
                    st.error("Invalid email address", icon="🚨")
                elif password != confirm_password:
                    st.error("Passwords do not match.", icon="🚨")
                else:
                    from AIT_DBConnector import db
                    db.connect()

                    select_query = "SELECT * FROM users WHERE email = %s"
                    params = (email,)
                    result = db.fetch_data(select_query, params)
                    time.sleep(2)
                    if len(result) == 0:
                        insert_query = "INSERT INTO users (name, email, role, password, verified) VALUES (%s, %s, %s, %s, %s)"
                        insert_params = (name, email, role, confirm_password, '0')
                        db.insert_data(insert_query, insert_params)
                        st.text("Please wait")

                        time.sleep(5)

                        select_query = "SELECT * FROM users WHERE email = %s"
                        params = (email,)
                        result = db.fetch_data(select_query, params)

                        if len(result) == 0:
                            st.error("Signup failed! You will receive signup details once verified.", icon="🚨")
                        elif len(result) == 1:
                            st.success(
                                f"Signup successful! You will receive confirmation email once approved by admin. Thanks {result[0]['name']}!")

                            from files.emailController import send_email_user
                            send_email_user(name, email, password)
                            time.sleep(2)

                            from files.emailController import send_email_user, send_email_admin
                            send_email_admin(email)
                            time.sleep(2)

                            st.rerun()
                    else:
                        st.error("This email address is already registered.", icon="🚨")
                    db.close()
        else:
            st.error('CAPTCHA verification failed. Try again.')