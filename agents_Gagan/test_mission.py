import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_experimental_option("detach", True)
service = Service()
driver = webdriver.Chrome(service=service, options=options)
driver.maximize_window()

driver.get("https://practicetestautomation.com/practice-test-login/")

# Enter username
username = driver.find_element(By.XPATH, '//input[@  id="username" ]')
username.send_keys("student")

# Enter password
password = driver.find_element(By.XPATH, '//input[@id="password"]')
password.send_keys("Password123")

# Click submit
submit_button = driver.find_element(By.XPATH, '//button[@  id="submit" ]')
submit_button.click()

# Click contact
contact_link = driver.find_element(By.XPATH, "//a[text()='Contact']")
contact_link.click()

# Click logout
logout_link = driver.find_element(By.XPATH, "//a[text()='Log out']")
logout_link.click()

# Wait 15 seconds for manual inspection
time.sleep(15)

# Wait additional 10 seconds before end
time.sleep(10)