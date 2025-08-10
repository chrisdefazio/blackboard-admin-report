## Blackboard (SOLE) Admin Report Generator

A small weekend project to simulate Blackboard Learn (Anthology Learn) admin tasks:  
loading course, user, and enrollment data, applying filters, and generating reports.

**🔗 [View Sample HTML Report](https://chrisdefazio.github.io/blackboard-admin-report/)**  
**📄 [Download Sample CSV Output](out/enrollment_report.csv)**


---

![CLI demo](assets/blackboard.gif)

### Quick start

1. Clone the repo & create a Python 3.11+ virtualenv  
2. `pip install -r requirements.txt`  
3. `python scripts/report_generator.py generate`

### CLI examples

```
# Filter to a course label substring
python scripts/report_generator.py --course-filter CS101

# Only show available courses/users/enrollments
python scripts/report_generator.py --only-available

# Toggle roles
python scripts/report_generator.py --no-include-students
python scripts/report_generator.py --no-include-instructors

# Custom locations
python scripts/report_generator.py --data-dir ./data --out-dir ./out
```

Flags (Typer):

- `--data-dir PATH` (default `./data`)
- `--course-filter TEXT`
- `--include-instructors / --no-include-instructors` (default include)
- `--include-students / --no-include-students` (default include)
- `--only-available`
- `--out-dir PATH` (default `./out`)

### Data dictionary (mock Learn Public v1 shape)

- `courses.json` (array of Course)
  - `id`: Learn internal id (e.g., `_12345_1`)
  - `courseId`: SIS-style id (e.g., `CS101-2025FA`)
  - `name`: course title
  - `description`: optional
  - `availability.available`: "Yes" | "No"

- `users.json` (array of User)
  - `id`: Learn internal id
  - `userName`: login name
  - `name.given`, `name.family`
  - `contact.email`: must contain `@`
  - `availability.available`: "Yes" | "No"

- `enrollments.json` (array of Enrollment)
  - `id`: Learn internal id
  - `userId`: references `users.id`
  - `courseId`: references `courses.id` (internal id)
  - `type`: role category (validated, unknown values only warn)
  - `role`: functional role (validated, unknown values only warn)
  - `availability.available`: boolean

### How it works (transform pipeline)

- Validate JSON into Pydantic models
- Normalize availability to booleans
- Inner-join enrollments ↔ users ↔ courses with pandas
- Derive `userFullName` and `courseLabel`
- Apply filters (role toggles, course substring, only-available)
- Emit CSV, HTML (Jinja2), and `audit.json`

### Adapting to the real Learn REST API

Replace the file loaders with HTTP calls to Learn Public v1:

- Courses: `GET /learn/api/public/v1/courses`
- Users: `GET /learn/api/public/v1/users`
- Enrollments: `GET /learn/api/public/v1/courses/{courseId}/users` or `GET /learn/api/public/v1/users/{userId}/courses`

Auth: OAuth 2.0 Client Credentials

- Obtain Client ID/Secret from Anthology Developer Portal
- Token endpoint: exchange client credentials for bearer token
- Send `Authorization: Bearer <token>` on each request

Pagination and backoff

- Use `?limit` and `?offset` (or `nextPage` where available) to page through results
- Implement retry with exponential backoff on `429 Too Many Requests` (respect `Retry-After` header when present)
- Stream results into DataFrames, then reuse the same transform/report functions from this repo

### Testing

```
pytest -q
```

Tests cover model validation, warnings on unknown roles, filtering behavior, and artifact emission.

### Mock data

`data/*_wrapped.json` files mimic Learn's paged list responses with `{ "results": [...], "paging": { "nextPage": null } }`.

---

## References

- [Blackboard Learn REST API – Public v1](https://developer.blackboard.com/portal/displayApi/Learn) – Official Anthology/Blackboard API documentation used to shape mock JSON and data models.
- [Anthology Developer Portal](https://developer.anthology.com/portal) – OAuth setup, client credentials flow, and endpoint references.
- [Blackboard REST API Getting Started Guide](https://docs.blackboard.com/learn/rest/getting-started) – Overview of authentication and API usage.
