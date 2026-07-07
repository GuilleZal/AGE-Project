# Session Display Specification

## Purpose

Defines the current user/role display in `MainWindow` and the logout flow that returns the application to the login screen.

## Requirements

### Requirement: User and Role Display

`MainWindow` SHALL display the current username and role label in the top bar (e.g., "admin - Administrador"). The display MUST be read-only and visible at all times while the main window is open.

#### Scenario: Admin sees their identity

- GIVEN an admin user is authenticated
- WHEN `MainWindow` renders
- THEN a label displays "admin - Administrador" in the top bar area

#### Scenario: Cajero sees their identity

- GIVEN a cajero user "cajero1" is authenticated
- WHEN `MainWindow` renders
- THEN a label displays "cajero1 - Cajero" in the top bar area

### Requirement: Logout Button

`MainWindow` SHALL provide a "Cerrar sesion" button in the top bar. Clicking it SHALL: close the current session (set `logout_time`), destroy `MainWindow`, and return to `LoginView`.

#### Scenario: Logout returns to login screen

- GIVEN a user is logged in and `MainWindow` is open
- WHEN "Cerrar sesion" is clicked
- THEN the session row in `sessions` gets `logout_time` set
- AND `MainWindow` is destroyed
- AND `LoginView` is displayed

#### Scenario: After logout, new user can log in

- GIVEN a logout has been performed
- WHEN a different user enters valid credentials on the login screen
- THEN a new session is created for that user
- AND `MainWindow` opens with the new user's permissions

### Requirement: Application Exit During Session

Closing `MainWindow` via the window manager (X button) SHALL close the active session (set `logout_time`) before terminating.

#### Scenario: Window close ends session

- GIVEN a user is logged in with an open session
- WHEN the window manager close button is clicked
- THEN the session row gets `logout_time` set before the process exits
