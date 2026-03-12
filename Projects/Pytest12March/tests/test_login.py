import pytest
from pytest_bdd import scenarios, given, when, then
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pytest_bdd import scenarios
import Projects.Pytest12March.steps.login_steps
scenarios('../features/login.feature')

# from pytest_bdd import scenarios
#
# # Import step definitions so pytest can discover them
# from steps import login_steps
#
# scenarios('../features/login.feature')

# scenarios('../features/login.feature')
#
# @given('I have navigated to the login page of the application')
# def navigate_to_login_page(browser):
#     browser.get('https://bigappmarket-dev.appiancloud.com/suite/sites/demo-qpr-underwriting-workbench')
#
# @when('I enter a valid username')
# def enter_valid_username(browser):
#     username_field = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, 'un')))
#     username_field.send_keys('neeraj.kumar@bitsinglass.com')
#
# @when('I enter a valid password')
# def enter_valid_password(browser):
#     password_field = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, 'pw')))
#     password_field.send_keys('Neeraj@123$')
#
# @when('I click on the "Login" button')
# def click_login_button(browser):
#     login_button = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.ID, 'jsLoginButton')))
#     login_button.click()
#
# @when('I click on the "Monitoring" tab')
# def click_monitoring_tab(browser):
#     monitoring_tab = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH, "//ul/li[@class='VirtualNavigationMenuTab_MERCURY_TOPBAR---nav_tab VirtualNavigationMenuTab_MERCURY_TOPBAR---top_level_tab' and @title='Monitoring']/a")))
#     monitoring_tab.click()
#
# @then('I click on the "Create Chart" button')
# def click_create_chart_button(browser):
#     create_chart_button = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Create Chart']")))
#     create_chart_button.click()