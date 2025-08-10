## Blackboard (SOLE) Admin Prep – Enrollment Report

A small weekend project to simulate Blackboard Learn (Anthology Learn) admin tasks:  
loading course, user, and enrollment data, applying filters, and generating clean reports.

**🔗 Live HTML Report:** [View here](https://chrisdefazio.github.io/blackboard-admin-report/)  
**📂 Repo:** [GitHub](https://github.com/chrisdefazio/blackboard-admin-report)  
**📄 CSV Output:** [enrollment_report.csv](out/enrollment_report.csv)

---

### Quick start

1) Python 3.11+

2) Create a venv and install deps

```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

3) Generate the report (uses `data/` by default, writes to `out/`)

```
python scripts/report_generator.py --help
python scripts/report_generator.py
```

Artifacts are written to `out/`:

- `enrollment_report.csv`
- `enrollment_report.html`
- `audit.json`

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

### Screenshots

Add screenshots of the HTML report after running with your data.
