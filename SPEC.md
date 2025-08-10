# Blackboard (SOLE) Admin Prep Project – SPEC

A small, weekend-ready project that simulates working with Blackboard Learn (a.k.a. Anthology Learn) REST APIs for courses, users, and enrollments. It uses **mock JSON** shaped like the public v1 API, a **Python** report generator, and produces admin-friendly outputs (CSV + HTML).

---

## Goals

* Demonstrate familiarity with LMS admin concepts: courses, users, enrollments, roles, availability.
* Show basic **API-shaped data handling** (without needing a real Learn instance): pagination, filtering, joins.
* Produce **clean artifacts** a hiring manager can scan: README, sample data, generated reports.

---

## Tech & Deliverables

* **Language:** Python 3.11+
* **Libraries:** `pydantic`, `pandas`, `jinja2`, `typer` (CLI), `pytest`
* **Outputs:**

  * `/out/enrollment_report.csv`
  * `/out/enrollment_report.html` (styled table, simple summary)
  * `/out/audit.json` (run metadata: timestamp, filters, input sizes)
* **Docs:** `README.md` (how to run + how to adapt to real API), `SPEC.md` (this file)

---

## Repo Structure

```
blackboard-api-mock/
├─ data/
│  ├─ courses.json
│  ├─ users.json
│  └─ enrollments.json
├─ scripts/
│  └─ report_generator.py
├─ templates/
│  └─ report.html.j2
├─ out/               # generated
├─ tests/
│  ├─ test_models.py
│  └─ test_report.py
├─ README.md
└─ SPEC.md
```

---

## Mock Data Schemas (API-shaped)

> These mirror the **Learn Public v1** patterns but are simplified.

### `courses.json` (array)

```json
[
  {
    "id": "_12345_1",
    "courseId": "CS101-2025FA",
    "name": "Intro to Computer Science",
    "description": "Fundamentals of computing.",
    "availability": { "available": "Yes" }
  }
]
```

### `users.json` (array)

```json
[
  {
    "id": "_2001_1",
    "userName": "jdoe",
    "name": { "given": "Jane", "family": "Doe" },
    "contact": { "email": "jane.doe@example.edu" },
    "availability": { "available": "Yes" }
  }
]
```

### `enrollments.json` (array)

```json
[
  {
    "id": "_30001_1",
    "userId": "_2001_1",
    "courseId": "_12345_1",
    "type": "Student",          
    "role": "Student",
    "availability": { "available": true }
  }
]
```

**Notes**

* Treat `id` as Learn internal IDs (strings like `_12345_1`).
* `courseId` in courses is SIS-style (e.g., `CS101-2025FA`). In enrollments, `courseId` references the **course internal id**.
* `availability.available` can be `"Yes"/"No"` (courses/users) or boolean (enrollments).

---

## CLI Requirements (Typer)

Command: `python scripts/report_generator.py` with flags:

* `--data-dir PATH` (default: `./data`)
* `--course-filter TEXT` (substring match on `courseId` or `name`)
* `--include-instructors / --no-include-instructors` (default: include)
* `--include-students / --no-include-students` (default: include)
* `--only-available` (filter to available courses/users/enrollments)
* `--out-dir PATH` (default: `./out`)

Behavior:

* Load JSON, validate into Pydantic models.
* Join enrollments ↔ users ↔ courses.
* Apply filters (by role, availability, and course filter).
* Generate CSV + HTML + audit JSON.
* Exit code 0 on success; non-zero on validation/IO errors.

---

## Data Models (Pydantic)

* `Course`: id\:str, courseId\:str, name\:str, description\:Optional, availability.available: Literal\["Yes","No"]
* `User`: id\:str, userName\:str, name.given\:str, name.family\:str, contact.email\:str, availability.available: Literal\["Yes","No"]
* `Enrollment`: id\:str, userId\:str, courseId\:str, type\:str, role\:str, availability.available: bool

Validation rules:

* Email must contain `@`.
* `type`/`role` ∈ {`Instructor`,`TeachingAssistant`,`Student`,`Grader`,`Observer`} (flexible but warn on unknowns).
* Coerce whitespace; error on missing required fields.

---

## Transform & Report Logic

1. **Normalize** availability to booleans (`Yes`→True, `No`→False).
2. **Inner join** enrollments→users (userId=id) and enrollments→courses (courseId=id).
3. **Derived fields**

   * `userFullName = f"{given} {family}"`
   * `courseLabel = f"{courseId} – {name}"`
4. **Filters**

   * `only-available`: drop rows where any of course/user/enrollment availability is False.
   * `course-filter`: case-insensitive substring match on courseId or name.
   * role toggles based on flags.
5. **Outputs**

   * **CSV columns**: courseInternalId, courseId, courseName, userId, userName, userFullName, email, role, enrollmentAvailable, userAvailable, courseAvailable
   * **HTML**: table + summary counts (#courses, #users, #enrollments by role) rendered with Jinja2 template `templates/report.html.j2`.
   * **Audit JSON**: run timestamp, args, input sizes, output sizes, filter summary.

---

## HTML Template Requirements (`templates/report.html.j2`)

* Title: "Enrollment Report"
* Header summary with counts
* Searchable/sortable table (add a tiny vanilla JS table sort or keep static if time-boxed)
* Footer with generation timestamp

---

## Testing (Pytest)

* `test_models.py`

  * Valid course/user/enrollment parse succeeds.
  * Invalid email fails.
  * Unknown role logs warning (capture logs) but still loads.
* `test_report.py`

  * Filter flags produce expected row counts.
  * `only-available` removes unavailable joins.
  * CSV/HTML/audit files are created with expected columns/keys.

---

## README Content (Acceptance Checklist)

* Quick start (venv + `pip install -r requirements.txt`).
* How to run the CLI with examples.
* Data dictionary for the mock JSON files.
* How to adapt to **real** Learn API:

  * Replace file loaders with requests to `/learn/api/public/v1/courses`, `/users`, `/enrollments`.
  * Handle OAuth 2.0 client credentials (link to Anthology developer portal).
  * Handle pagination (`?limit`, `?offset`) and 429 backoff.
* Screenshots of the HTML report.

---

## Stretch Goals (Optional)

* Add **CSV import** for creating mock enrollments.
* Add **role-level summaries** per course (pivot table in HTML).
* Wire up a minimal **FastAPI** endpoint to serve the HTML report.
* Add **Mermaid** diagram in README showing data flow (Admin → API → Report).

---

## Cursor Prompts (Use These Blocks)

**1) Plan**

```
Create a Python project per SPEC.md. Scaffold the folders and minimal files, add a requirements.txt with pandas, pydantic, typer, jinja2, pytest. Generate example mock JSON matching SPEC. Add a simple Jinja2 template. Write a README skeleton.b
```

**2) Implement**

```
Implement pydantic models for Course, User, Enrollment with validation. Implement a loader that reads JSON arrays from /data. Implement CLI with Typer per flags. Join data with pandas, apply filters, and write CSV/HTML/audit. Keep functions small and testable.
```

**3) Test**

```
Write pytest tests per SPEC. Use small inline fixtures to simulate data. Ensure CSV/HTML/audit are emitted and role/availability filters work.
```

**4) Polish**

```
Improve the Jinja2 HTML with a summary header and readable table. Add README instructions for adapting to the real Blackboard Learn REST API (OAuth, endpoints, pagination). Add screenshots once the HTML renders.
```

---

## Acceptance Criteria

* ✅ Repo builds and runs: `python scripts/report_generator.py --help` works
* ✅ CSV, HTML, and audit JSON generated under `/out` with default data
* ✅ Filters operate as described; tests pass
* ✅ README clearly explains how to adapt to real Learn API and shows screenshots
* ✅ Code is clean, typed, and organized for quick review
