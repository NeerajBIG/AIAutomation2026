import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import streamlit as st

sender_email = "neeraj1wayitsol@gmail.com"  # Replace with your email
sender_password = "gwgc ioef ymbx yybo"
AdminEmail = "neerajpebmaca@gmail.com"

def send_email_user(user, email, password):
    recipient_email = email

    subject = "Registration Confirmation"
    body = f"Hello {user}, \n\nYour registration is successful! You will receive confirmation email once approved by admin. \n\n Your access details are as follows \n\nEmail: {email}\nPassword: {password}\nlink: https://bigauto.streamlit.app/\n\nThank you for signing up."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Set up the server
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
    except Exception as e:
        st.error(f"Error sending email: {e}")


def send_email_admin(email):
    recipient_email = AdminEmail

    subject = "New Registration for approval"
    body = f"Hello Admin, \n\n {email} just registered! Please confirm user's request. \n\n Link to admin portal is as follows \n\n link: https://bigautoapp.streamlit.app/\n\nHave a nice day."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
    except Exception as e:
        st.error(f"Error sending email: {e}")