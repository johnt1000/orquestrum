# Auth Service (v1)

Minimal authentication service (email/password) scaffold.

Quickstart

1. Copy .env.example to .env and set values
2. npm install
3. npm run dev
4. GET http://localhost:3000/health should return 200

Endpoints (v1)

- GET /health — healthcheck
- POST /register — register user (email, password)
- POST /login — login (email, password)
- POST /logout — logout (authenticated)
