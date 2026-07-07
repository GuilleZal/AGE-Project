# User Management Specification

## Purpose

Defines the admin-only interface for creating, listing, editing, and deactivating users. Only the `admin` role MAY access this module.

## Requirements

### Requirement: Access Control

The user management module SHALL be accessible only to the `admin` role. The system SHALL expose it as a tab or button in `MainWindow` visible exclusively to admin.

#### Scenario: Admin sees user management entry

- GIVEN an admin user is authenticated
- WHEN `MainWindow` renders
- THEN a "Usuarios" tab or button is visible

#### Scenario: Non-admin cannot access user management

- GIVEN a gerente user is authenticated
- WHEN `MainWindow` renders
- THEN no "Usuarios" tab or button is visible

### Requirement: User Creation Form

The system SHALL provide a form with: username (text, required, unique), password (text, required), and role selection (dropdown with values: `gerente`, `cajero`, `inventario`). The `admin` role MUST NOT appear in the dropdown. Submitting the form SHALL insert a new row into `users` with `is_active=1`.

#### Scenario: Admin creates a cajero user

- GIVEN the admin is on the user creation form
- WHEN username="cajero1", password="pass123", role="cajero" are submitted
- THEN a new user row is created with `is_active=1`, `role='cajero'`
- AND the user appears in the user list

#### Scenario: Duplicate username rejected

- GIVEN a user with `username='cajero1'` already exists
- WHEN the admin tries to create another user with `username='cajero1'`
- THEN an error message "El nombre de usuario ya existe" is displayed
- AND no new row is inserted

#### Scenario: Empty fields rejected

- GIVEN the admin is on the user creation form
- WHEN submit is pressed with empty username or password
- THEN an error message "Complete todos los campos" is displayed

### Requirement: User List View

The system SHALL display a list of all users showing: username, role, and active status. The admin bootstrap user MUST appear in the list but MUST NOT be editable or deactivatable.

#### Scenario: Admin views user list

- GIVEN 3 users exist (admin, gerente1, cajero1)
- WHEN the user management view loads
- THEN the list shows all 3 users with their roles and active status

#### Scenario: Admin user not editable

- GIVEN the admin bootstrap user is in the list
- WHEN the admin selects the admin row
- THEN the edit and deactivate controls are disabled or hidden for that row

### Requirement: User Edit and Deactivation

The system SHALL allow editing a user's password and role, and toggling `is_active` between 1 and 0. Deactivating a user with an open session SHALL NOT terminate the session immediately (the session ends on next login attempt).

#### Scenario: Admin deactivates a user

- GIVEN user `cajero1` is active
- WHEN admin clicks deactivate on `cajero1`
- THEN `cajero1.is_active` is set to 0
- AND `cajero1` cannot log in on next attempt

#### Scenario: Admin changes user role

- GIVEN user `gerente1` has role `gerente`
- WHEN admin changes role to `cajero` and saves
- THEN `gerente1.role` is updated to `cajero`
- AND the permission matrix reflects the new role on next login

#### Scenario: Admin changes user password

- GIVEN user `cajero1` exists
- WHEN admin sets a new password and saves
- THEN `cajero1` can log in with the new password
- AND the old password no longer works
