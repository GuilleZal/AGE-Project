# User Authentication Specification

## Purpose

Defines the login flow: credential validation, session creation, the login screen UI, the hardcoded admin bootstrap, and the test-mode bypass that keeps existing tests green.

## Requirements

### Requirement: Admin Bootstrap

The system SHALL create a hardcoded admin user (`admin` / `admin123`, role `admin`) on first database initialization. The user MUST NOT be duplicated on subsequent starts. The admin user MUST NOT be deletable or renamable via the user management interface.

#### Scenario: First application start creates admin user

- GIVEN an empty or newly created database
- WHEN `init_db` executes
- THEN a row exists in `users` with `username='admin'`, `password='admin123'`, `role='admin'`, `is_active=1`

#### Scenario: Subsequent start does not duplicate admin

- GIVEN a database where the admin user already exists
- WHEN `init_db` executes again
- THEN exactly one row with `username='admin'` exists

### Requirement: Credential Validation

The system SHALL validate credentials by exact match against the `users` table. An inactive user (`is_active=0`) MUST be rejected even if credentials match.

#### Scenario: Valid credentials for active user

- GIVEN an active user with `username='gerente1'`, `password='pass123'`
- WHEN `AuthService.login('gerente1', 'pass123')` is called
- THEN the method returns the `User` dataclass for that user

#### Scenario: Wrong password

- GIVEN an active user with `username='gerente1'`
- WHEN `AuthService.login('gerente1', 'wrong')` is called
- THEN the method returns `None`

#### Scenario: Inactive user

- GIVEN an inactive user with `username='old_cajero'`, `is_active=0`
- WHEN `AuthService.login('old_cajero', 'pass123')` is called
- THEN the method returns `None`

#### Scenario: Non-existent username

- GIVEN no user with `username='ghost'`
- WHEN `AuthService.login('ghost', 'pass')` is called
- THEN the method returns `None`

### Requirement: Login Screen UI

The system SHALL display a `LoginView` window before `MainWindow` when no active session exists. The view MUST contain: a username text field, a password field (masked input), a "Iniciar sesion" button, and an error label (hidden by default). Pressing Enter in either field MUST trigger login.

#### Scenario: Login screen appears on cold start

- GIVEN no active session
- WHEN the application starts
- THEN `LoginView` is displayed and `MainWindow` is NOT created

#### Scenario: Successful login transitions to MainWindow

- GIVEN the login screen is visible
- WHEN valid credentials are entered and submitted
- THEN `LoginView` closes and `MainWindow` opens with the authenticated user context

#### Scenario: Failed login shows error

- GIVEN the login screen is visible
- WHEN invalid credentials are submitted
- THEN the error label displays "Usuario o contrasena incorrectos" and focus returns to the username field

#### Scenario: Empty fields show validation error

- GIVEN the login screen is visible
- WHEN the submit button is pressed with empty username or password
- THEN the error label displays "Complete todos los campos"

### Requirement: Session Lifecycle

On successful login the system SHALL insert a row into `sessions` with `user_id`, `login_time`, and `logout_time=NULL`. On logout the system SHALL set `logout_time` to the current timestamp. Only one session row may have `logout_time=NULL` per user at any time.

#### Scenario: Session record created on login

- GIVEN user with `id=2` logs in successfully
- WHEN `AuthService.login` completes
- THEN a `sessions` row exists with `user_id=2`, `logout_time IS NULL`

#### Scenario: Logout closes session

- GIVEN an open session for `user_id=2`
- WHEN `AuthService.logout(user_id=2)` is called
- THEN the session row has `logout_time` set to current timestamp

### Requirement: Test Mode Bypass

The system SHALL support a `test_mode` flag (environment variable `POS_TEST_MODE=1` or constructor parameter) that skips the login screen and creates a synthetic admin session. All 21 existing test files MUST continue to pass without modification.

#### Scenario: Test mode skips login

- GIVEN `POS_TEST_MODE=1` is set
- WHEN the application starts
- THEN `MainWindow` opens directly with a synthetic admin user context, no `LoginView` is shown

#### Scenario: Existing tests unaffected

- GIVEN the `db` fixture from `conftest.py` (in-memory SQLite)
- WHEN existing tests run
- THEN all 21 test files pass without changes to their assertions or fixtures
