from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional, Sequence, Tuple

import pandas as pd
import typer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, ValidationError, ValidationInfo, field_validator


# Logging configuration
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


# ------------------------------
# Pydantic Models
# ------------------------------

AllowedYesNo = Literal["Yes", "No"]


class AvailabilityYesNo(BaseModel):
    """Availability model for Courses and Users with Yes/No semantics."""

    available: AllowedYesNo


class AvailabilityBool(BaseModel):
    """Availability model for Enrollments with boolean semantics."""

    available: bool


class UserName(BaseModel):
    given: str
    family: str

    @field_validator("given", "family", mode="before")
    def _strip(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class Contact(BaseModel):
    email: str

    @field_validator("email", mode="before")
    def _strip_and_validate_email(cls, value: str) -> str:
        value = value.strip() if isinstance(value, str) else value
        if not isinstance(value, str) or "@" not in value:
            raise ValueError("Invalid email: missing '@'")
        return value


class Course(BaseModel):
    """Simplified Course model shaped like Learn public v1."""

    id: str
    courseId: str
    name: str
    description: Optional[str] = None
    availability: AvailabilityBool

    @field_validator("id", "courseId", "name", "description", mode="before")
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


ALLOWED_ROLES: set[str] = {
    "Instructor",
    "TeachingAssistant",
    "Student",
    "Grader",
    "Observer",
}


class User(BaseModel):
    """Simplified User model shaped like Learn public v1."""

    id: str
    userName: str
    name: UserName
    contact: Contact
    availability: AvailabilityBool

    @field_validator("id", "userName", mode="before")
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class Enrollment(BaseModel):
    id: str
    userId: str
    courseId: str
    role: str
    availability: AvailabilityBool

    @field_validator("id", "userId", "courseId", "role", mode="before")
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("role")
    def _warn_unknown_role(cls, value: str):
        if value not in ALLOWED_ROLES:
            logger.warning("Unknown role: %s", value)
        return value



# ------------------------------
# Data loading utilities
# ------------------------------

def _read_json_array(file_path: Path) -> List[dict]:
    """Read a JSON array file and return list of dicts."""

    try:
        with file_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing required data file: {file_path}") from exc
    if not isinstance(payload, list):
        raise ValueError(f"Expected an array in {file_path}, got {type(payload).__name__}")
    return payload


def load_courses(data_dir: Path) -> List[Course]:
    """Load and validate courses from courses.json, normalizing availability."""

    raw = _read_json_array(data_dir / "courses.json")
    normalized: List[dict] = []
    for item in raw:
        item_copy = dict(item)
        avail = ((item_copy.get("availability") or {}).get("available"))
        item_copy["availability"] = {"available": _coerce_available_to_bool(avail)}
        normalized.append(item_copy)
    return [Course(**item) for item in normalized]


def load_users(data_dir: Path) -> List[User]:
    """Load and validate users from users.json, normalizing availability."""

    raw = _read_json_array(data_dir / "users.json")
    normalized: List[dict] = []
    for item in raw:
        item_copy = dict(item)
        avail = ((item_copy.get("availability") or {}).get("available"))
        item_copy["availability"] = {"available": _coerce_available_to_bool(avail)}
        normalized.append(item_copy)
    return [User(**item) for item in normalized]


def _coerce_available_to_bool(value: object) -> bool:
    """Coerce availability 'available' field from Yes/No/boolean to boolean."""
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"yes", "true", "y", "1"}:
            return True
        if lowered in {"no", "false", "n", "0"}:
            return False
    if isinstance(value, bool):
        return value
    # Fallback: treat unknown truthy as False to be conservative
    return False


def load_enrollments(data_dir: Path) -> List[Enrollment]:
    """Load and validate enrollments from enrollments.json, normalizing availability."""

    raw = _read_json_array(data_dir / "enrollments.json")
    normalized: List[dict] = []
    for item in raw:
        item_copy = dict(item)
        avail = ((item_copy.get("availability") or {}).get("available"))
        item_copy["availability"] = {"available": _coerce_available_to_bool(avail)}
        normalized.append(item_copy)
    return [Enrollment(**item) for item in normalized]


# ------------------------------
# Transform helpers
# ------------------------------

def _yes_no_to_bool(value: AllowedYesNo) -> bool:
    return value == "Yes"


def yes_no(value: bool) -> str:
    """Convert boolean to Learn-style Yes/No string for HTML rendering."""
    return "Yes" if bool(value) else "No"

def _build_dataframes(
    courses: Sequence[Course], users: Sequence[User], enrollments: Sequence[Enrollment]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convert validated models into pandas DataFrames with normalized fields."""

    courses_df = pd.DataFrame(
        [
            {
                "courseInternalId": c.id,
                "courseId": c.courseId,
                "courseName": c.name,
                "term": c.courseId.split("-")[-1] if "-" in c.courseId else "",
                "courseAvailable": c.availability.available,
            }
            for c in courses
        ]
    )

    users_df = pd.DataFrame(
        [
            {
                "userId": u.id,
                "userName": u.userName,
                "given": u.name.given,
                "family": u.name.family,
                "email": u.contact.email,
                "userAvailable": u.availability.available,
            }
            for u in users
        ]
    )

    enrollments_df = pd.DataFrame(
        [
            {
                "enrollmentId": e.id,
                "userId": e.userId,
                "courseInternalId": e.courseId,
                "role": e.role,
                "enrollmentAvailable": e.availability.available,
            }
            for e in enrollments
        ]
    )

    return courses_df, users_df, enrollments_df


def _join_frames(
    courses_df: pd.DataFrame, users_df: pd.DataFrame, enrollments_df: pd.DataFrame
) -> pd.DataFrame:
    """Inner join enrollments to users and courses; add derived fields."""

    if any(df.empty for df in (courses_df, users_df, enrollments_df)):
        # Ensure required columns exist even when empty
        for df, cols in (
            (courses_df, ["courseInternalId", "courseId", "courseName", "term", "courseAvailable"]),
            (
                users_df,
                ["userId", "userName", "given", "family", "email", "userAvailable"],
            ),
            (
                enrollments_df,
                ["enrollmentId", "userId", "courseInternalId", "role", "enrollmentAvailable"],
            ),
        ):
            for col in cols:
                if col not in df.columns:
                    df[col] = pd.Series([], dtype="object")

    df = enrollments_df.merge(users_df, on="userId", how="inner").merge(
        courses_df, on="courseInternalId", how="inner"
    )

    # Derived fields
    df["userFullName"] = (df["given"].fillna("") + " " + df["family"].fillna("")).str.strip()
    df["courseLabel"] = df["courseId"].astype(str) + " – " + df["courseName"].astype(str)
    return df


def _apply_filters(
    joined_df: pd.DataFrame,
    course_filter: Optional[str],
    include_instructors: bool,
    include_students: bool,
    only_available: bool,
) -> pd.DataFrame:
    """Apply filters per SPEC to the joined DataFrame."""

    df = joined_df.copy()

    # Availability: keep rows where all three are available
    if only_available and not df.empty:
        df = df[
            (df["courseAvailable"]) & (df["userAvailable"]) & (df["enrollmentAvailable"])
        ]

    # Course substring filter (case-insensitive) on courseId or courseName
    if course_filter:
        needle = course_filter.lower()
        df = df[
            df["courseId"].str.lower().str.contains(needle, na=False)
            | df["courseName"].str.lower().str.contains(needle, na=False)
        ]

    # Role toggles: include_instructors => non-Student, include_students => Student
    if not (include_instructors and include_students):
        role_series = df["role"].astype(str)
        is_student = role_series.str.lower() == "student"
        keep_mask = pd.Series(False, index=df.index)
        if include_students:
            keep_mask = keep_mask | is_student
        if include_instructors:
            keep_mask = keep_mask | (~is_student)
        df = df[keep_mask]

    return df


def _prepare_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order CSV columns per SPEC."""

    csv_columns = [
        "courseInternalId",
        "courseId",
        "courseName",
        "term",
        "userId",
        "userName",
        "userFullName",
        "email",
        "role",
        "enrollmentAvailable",
        "userAvailable",
        "courseAvailable",
    ]
    return df.loc[:, csv_columns].copy() if not df.empty else pd.DataFrame(columns=csv_columns)


def _render_html(template_dir: Path, rows: List[Dict[str, object]], summary: Dict[str, int]) -> str:
    """Render HTML content using Jinja2 template report.html.j2."""

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")
    rendered = template.render(
        rows=rows,
        summary=summary,
        generated_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        yes_no=yes_no,
    )
    return rendered


def generate_report(
    data_dir: Path,
    out_dir: Path,
    course_filter: Optional[str],
    include_instructors: bool,
    include_students: bool,
    only_available: bool,
) -> Tuple[Path, Path, Path]:
    """Load data, transform with pandas, apply filters, and write CSV/HTML/audit.

    Returns paths to (csv_path, html_path, audit_path).
    """

    # Load and validate
    courses = load_courses(data_dir)
    users = load_users(data_dir)
    enrollments = load_enrollments(data_dir)

    # DataFrames and joins
    courses_df, users_df, enrollments_df = _build_dataframes(courses, users, enrollments)
    joined_df = _join_frames(courses_df, users_df, enrollments_df)
    filtered_df = _apply_filters(
        joined_df, course_filter, include_instructors, include_students, only_available
    )

    # Ensure output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_df = _prepare_csv(filtered_df)
    # Map booleans to "Yes"/"No" for display
    for col in ("enrollmentAvailable", "userAvailable", "courseAvailable"):
        if col in csv_df.columns:
            csv_df[col] = csv_df[col].map(yes_no)

    csv_path = out_dir / "enrollment_report.csv"
    csv_df.to_csv(csv_path, index=False)

    # HTML
    rows_for_html = [
        {
            "courseLabel": r["courseLabel"],
            "term": r["term"],
            "userFullName": r["userFullName"],
            "role": r["role"],
            "enrollmentAvailable": bool(r["enrollmentAvailable"]),
            "userAvailable": bool(r["userAvailable"]),
            "courseAvailable": bool(r["courseAvailable"]),
        }
        for _, r in filtered_df.iterrows()
    ]
    summary = {
        "courses": int(filtered_df["courseInternalId"].nunique()) if not filtered_df.empty else 0,
        "users": int(filtered_df["userId"].nunique()) if not filtered_df.empty else 0,
        "enrollments": int(len(filtered_df)),
    }
    template_dir = Path(__file__).resolve().parent.parent / "templates"
    html_content = _render_html(template_dir, rows_for_html, summary)
    html_path = out_dir / "enrollment_report.html"
    html_path.write_text(html_content, encoding="utf-8")

    # Audit JSON
    audit = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "args": {
            "data_dir": str(data_dir),
            "out_dir": str(out_dir),
            "course_filter": course_filter,
            "include_instructors": include_instructors,
            "include_students": include_students,
            "only_available": only_available,
        },
        "input_sizes": {
            "courses": len(courses),
            "users": len(users),
            "enrollments": len(enrollments),
        },
        "output_sizes": {
            "csv_rows": int(len(csv_df)),
            "unique_courses": summary["courses"],
            "unique_users": summary["users"],
        },
        "filters": {
            "only_available": only_available,
            "course_filter": course_filter,
            "roles_included": {
                "instructors": include_instructors,
                "students": include_students,
            },
        },
    }
    audit_path = out_dir / "audit.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    return csv_path, html_path, audit_path


# ------------------------------
# CLI
# ------------------------------

app = typer.Typer(add_completion=False, help="Generate Blackboard enrollment report")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    data_dir: Path = typer.Option(
        Path("./data"),
        "--data-dir",
        dir_okay=True,
        file_okay=False,
        readable=True,
        help="Directory containing courses.json, users.json, enrollments.json",
    ),
    course_filter: Optional[str] = typer.Option(
        None, "--course-filter", help="Substring match on courseId or course name"
    ),
    include_instructors: bool = typer.Option(
        True,
        "--include-instructors/--no-include-instructors",
        help="Include Instructor roles",
    ),
    include_students: bool = typer.Option(
        True, "--include-students/--no-include-students", help="Include Student roles"
    ),
    only_available: bool = typer.Option(
        False, "--only-available", help="Filter to only available courses/users/enrollments"
    ),
    out_dir: Path = typer.Option(
        Path("./out"), "--out-dir", help="Output directory for CSV, HTML, and audit JSON"
    ),
):
    """Root command: runs report generation when no subcommand is invoked."""
    if ctx.invoked_subcommand is not None:
        return
    try:
        csv_path, html_path, audit_path = generate_report(
            data_dir=data_dir,
            out_dir=out_dir,
            course_filter=course_filter,
            include_instructors=include_instructors,
            include_students=include_students,
            only_available=only_available,
        )
        typer.secho(f"Wrote: {csv_path} | {html_path} | {audit_path}", fg=typer.colors.GREEN)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def generate(
    data_dir: Path = typer.Option(
        Path("./data"),
        "--data-dir",
        dir_okay=True,
        file_okay=False,
        readable=True,
        help="Directory containing courses.json, users.json, enrollments.json",
    ),
    course_filter: Optional[str] = typer.Option(
        None, "--course-filter", help="Substring match on courseId or course name"
    ),
    include_instructors: bool = typer.Option(
        True,
        "--include-instructors/--no-include-instructors",
        help="Include Instructor roles",
    ),
    include_students: bool = typer.Option(
        True, "--include-students/--no-include-students", help="Include Student roles"
    ),
    only_available: bool = typer.Option(
        False, "--only-available", help="Filter to only available courses/users/enrollments"
    ),
    out_dir: Path = typer.Option(
        Path("./out"), "--out-dir", help="Output directory for CSV, HTML, and audit JSON"
    ),
):
    """Generate CSV, HTML, and audit JSON from mock Blackboard API-shaped data."""

    try:
        csv_path, html_path, audit_path = generate_report(
            data_dir=data_dir,
            out_dir=out_dir,
            course_filter=course_filter,
            include_instructors=include_instructors,
            include_students=include_students,
            only_available=only_available,
        )
        typer.secho(f"Wrote: {csv_path} | {html_path} | {audit_path}", fg=typer.colors.GREEN)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

