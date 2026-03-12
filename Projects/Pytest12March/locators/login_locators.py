from selenium.webdriver.common.by import By
class LoginLocators:
    USERNAME = (By.ID, "un")
    PASSWORD = (By.ID, "pw")
    LOGIN_BUTTON = (By.ID, "jsLoginButton")