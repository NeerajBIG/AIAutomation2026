from pytest_bdd import given, when, then
from Projects.Pytest12March.pages.login_page import LoginPage


@given('I have navigated to the login page of the application')
def navigate_to_login_page(browser):
    LoginPage(browser).open_login_page()

@when('I enter a valid username')
def enter_username(browser):
    LoginPage(browser).enter_username()

@when('I enter a valid password')
def enter_password(browser):
    LoginPage(browser).enter_password()

@then('I click on the "Login" button')
def click_login(browser):
    LoginPage(browser).click_login()