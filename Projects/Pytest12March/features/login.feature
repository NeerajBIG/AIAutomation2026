Feature: User Login Functionality
  # Description: User authentication validation for the application

  Background:
    Given I have navigated to the login page of the application

  @Positive @Smoke
  Scenario: Successful login with valid credentials
    When I enter a valid username
    And I enter a valid password
    Then I click on the "Login" button
