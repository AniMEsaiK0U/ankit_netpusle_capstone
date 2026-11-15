# NetPulse Capstone

This repository contains the Secure NetPulse Devices API project. The API uses
an in-memory device collection, public read endpoints, and JWT authentication
for all device writes. Data resets to the two sample devices whenever the
application restarts.

## Project structure

```text
api/
	main.py
	requirements.txt
	requirements-dev.txt
test/
	test_api.py
frontend/
logs/
scripts/
```

## Requirements

- Python 3.10 or newer
- A virtual environment

## Setup and run

Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r api/requirements-dev.txt

export DEMO_USERNAME="netpulse-user"
read -s -p "Training password: " DEMO_PASSWORD
printf '\n'
export DEMO_PASSWORD
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

python -m uvicorn main:app --app-dir api --host 127.0.0.1 --port 8000 --reload
```

The API is available at `http://127.0.0.1:8000`. Open
`http://127.0.0.1:8000/docs` for Swagger UI. Set all three environment
variables in the same terminal before starting the app. `JWT_SECRET` must be
at least 32 characters; use a new random value for each local environment. Do
not commit credentials or tokens. The `.env` file is ignored by Git.

## API contract

| Method | Endpoint | Access | Success |
| --- | --- | --- | --- |
| `GET` | `/` | Public | `200` |
| `POST` | `/auth/token` | Public | `200` |
| `GET` | `/devices` | Public | `200` |
| `GET` | `/devices/{device_id}` | Public | `200` |
| `POST` | `/devices` | Bearer token | `201` |
| `PUT` | `/devices/{device_id}` | Bearer token | `200` |
| `PATCH` | `/devices/{device_id}` | Bearer token | `200` |
| `DELETE` | `/devices/{device_id}` | Bearer token | `204` |

Device request fields are `name`, `device_type`, `status`, and `location`. The
API assigns each device an integer `id`. Missing devices return `404`; missing
or invalid bearer tokens and invalid logins return `401`; invalid request data
returns `422`.

## Verify the API

Run the integration tests from the repository root while the virtual
environment is active:

```bash
python -m pytest
```

The tests cover public reads, missing devices, rejected authentication,
password-form login, JWT subject and expiry claims, and the complete
authenticated create/replace/patch/delete lifecycle.

In Swagger, use `POST /auth/token` with the configured username and password
to authorize protected operations. The token response is sensitive; never
include a full token in screenshots or submitted documentation. Repeat the
same public and protected request flow in Postman when collecting project
evidence.

## Security notes

- The training password is hashed in memory; the plaintext password and
	signing key are loaded from environment variables, not source code.
- Tokens use HS256 and expire after 30 minutes. Protected routes verify the
	signature, expiry, and that the subject matches `DEMO_USERNAME`.
- Device data is not persisted. This is a local training API; use HTTPS before
	sending bearer tokens over any network beyond the local lab.