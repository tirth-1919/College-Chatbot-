# REST API v1 Specification

## Base URL
All API requests are versioned under:
`http://localhost:8000/api/v1`

Interactive Swagger/OpenAPI documentation is available at:
`http://localhost:8000/docs`

---

## 1. System Health
* **`GET /api/v1/health`**
  * Description: Real-time system and database connectivity status.
  * Public Endpoint: Yes.
  * Response:
    ```json
    {
      "status": "healthy",
      "service": "AI FAQ College Chat Bot Backend",
      "environment": "development",
      "version": "1.0.0",
      "database_connected": true,
      "timestamp": "2026-11-07T14:45:00Z"
    }
    ```

---

## 2. Authentication & Account
* **`POST /api/v1/auth/register`**
  * Description: Register a new user (`STUDENT`, `COLLEGE_ADMIN`, or `SUPER_ADMIN`).
  * Body: `{ "email", "password", "full_name", "role", "college_id" }`
* **`POST /api/v1/auth/login`**
  * Description: Authenticate and receive a signed JWT bearer token.
  * Body: `{ "email", "password" }`
  * Response:
    ```json
    {
      "success": true,
      "data": {
        "access_token": "eyJhbGciOi...",
        "token_type": "bearer",
        "expires_in_minutes": 60,
        "user_id": "...",
        "role": "COLLEGE_ADMIN",
        "college_id": "..."
      }
    }
    ```
* **`GET /api/v1/auth/me`**
  * Description: Retrieve profile of authenticated user.
  * Headers: `Authorization: Bearer <token>`
* **`POST /api/v1/auth/verify-email`**
  * Description: Validate 6-8 character email verification token.

---

## 3. Colleges & Tenants
* **`GET /api/v1/colleges`**
  * Description: Public directory of approved colleges.
* **`GET /api/v1/colleges/{id_or_slug}`**
  * Description: Detailed college institutional profile.
* **`POST /api/v1/colleges`**
  * Description: Register a new college onboarding request.
* **`PATCH /api/v1/colleges/{id}`**
  * Description: Update institutional details or approval status (Super Admin).

---

## 4. User Administration (Super Admin Only)
* **`GET /api/v1/users`**: List all platform accounts.
* **`GET /api/v1/users/{id}`**: Detailed user profile.
* **`PATCH /api/v1/users/{id}`**: Toggle user active state or role.

---

## 5. College Memberships
* **`POST /api/v1/memberships`**: Assign admin to a college tenant.
* **`GET /api/v1/memberships/college/{college_id}`**: List administrators for a college.

