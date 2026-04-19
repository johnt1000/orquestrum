# QA - Login system (v1)

Test cases:
1. Register with valid email+password -> 201
2. Register with existing email -> 409
3. Login with correct credentials -> 200 + session cookie
4. Login with incorrect password -> 401 (no info about which field is wrong)
5. Logout invalidates session -> subsequent calls 401
6. Multiple failed logins increment failed_login_count and lock account after threshold

Automated tests:
- Integration tests using Supertest
- Unit tests for hashing and lockout logic
