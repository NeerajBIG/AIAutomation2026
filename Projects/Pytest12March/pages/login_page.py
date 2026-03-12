from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Projects.Pytest12March.config.config import *
from Projects.Pytest12March.locators.login_locators import LoginLocators

class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def open_login_page(self):
        self.driver.get(BASE_URL)

    def enter_username(self):
        element = self.wait.until(
        EC.presence_of_element_located(LoginLocators.USERNAME)
        )
        element.send_keys(USERNAME)

    def enter_password(self):
        element = self.wait.until(
        EC.presence_of_element_located(LoginLocators.PASSWORD)
        )
        element.send_keys(PASSWORD)

    def click_login(self):
        element = self.wait.until(
        EC.element_to_be_clickable(LoginLocators.LOGIN_BUTTON)
        )
        element.click()