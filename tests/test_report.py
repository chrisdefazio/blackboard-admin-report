from pathlib import Path
from typing import List

import json
import pandas as pd
import pytest

from scripts import report_generator as rg


@pytest.fixture()
def sample_data():
    courses = [
        rg.Course(
            id="_c1_1",
            courseId="CS101-2025FA",
            name="Intro to CS",
            availability=rg.AvailabilityBool(available=True),
        ),
        rg.Course(
            id="_c2_1",
            courseId="HIST200-2025FA",
            name="World History",
            availability=rg.AvailabilityBool(available=False),
        ),
    ]

    users = [
        rg.User(
            id="_u1_1",
            userName="inst1",
            name=rg.UserName(given="Ina", family="Structor"),
            contact=rg.Contact(email="ina@school.edu"),
            availability=rg.AvailabilityBool(available=True),
        ),
        rg.User(
            id="_u2_1",
            userName="stud1",
            name=rg.UserName(given="Stu", family="Dent"),
            contact=rg.Contact(email="stu@school.edu"),
            availability=rg.AvailabilityBool(available=True),
        ),
        rg.User(
            id="_u3_1",
            userName="stud2",
            name=rg.UserName(given="Una", family="Vailable"),
            contact=rg.Contact(email="una@school.edu"),
            availability=rg.AvailabilityBool(available=False),
        ),
    ]

    enrollments = [
        rg.Enrollment(
            id="_e1_1",
            userId="_u1_1",
            courseId="_c1_1",
            type="Instructor",
            role="Instructor",
            availability=rg.AvailabilityBool(available=True),
        ),
        rg.Enrollment(
            id="_e2_1",
            userId="_u2_1",
            courseId="_c1_1",
            type="Student",
            role="Student",
            availability=rg.AvailabilityBool(available=True),
        ),
        rg.Enrollment(
            id="_e3_1",
            userId="_u3_1",
            courseId="_c2_1",
            type="Student",
            role="Student",
            availability=rg.AvailabilityBool(available=False),
        ),
    ]
    return courses, users, enrollments


def test_filters_and_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_data):
    courses, users, enrollments = sample_data

    # Monkeypatch loaders to return our inline fixtures
    monkeypatch.setattr(rg, "load_courses", lambda _p: courses)
    monkeypatch.setattr(rg, "load_users", lambda _p: users)
    monkeypatch.setattr(rg, "load_enrollments", lambda _p: enrollments)

    # Ensure template rendering does not require reading the repo template path
    def fake_render(_tmpl_dir: Path, rows, summary):
        # Return minimal HTML string
        return f"<html><body><h1>Enrollment Report</h1><p>Courses: {summary['courses']}</p></body></html>"

    monkeypatch.setattr(rg, "_render_html", fake_render)

    # Run full pipeline
    csv_path, html_path, audit_path = rg.generate_report(
        data_dir=Path("/does/not/matter"),
        out_dir=tmp_path,
        course_filter=None,
        include_instructors=True,
        include_students=True,
        only_available=False,
    )

    # Files exist
    assert csv_path.exists()
    assert html_path.exists()
    assert audit_path.exists()

    # CSV columns
    df = pd.read_csv(csv_path)
    expected_cols = [
        "courseInternalId",
        "courseId",
        "courseName",
        "userId",
        "userName",
        "userFullName",
        "email",
        "role",
        "enrollmentAvailable",
        "userAvailable",
        "courseAvailable",
    ]
    assert list(df.columns) == expected_cols

    # With only_available flag, the enrollment with unavailable user/course/enrollment drops
    csv_path2, html_path2, audit_path2 = rg.generate_report(
        data_dir=Path("/does/not/matter"),
        out_dir=tmp_path,
        course_filter=None,
        include_instructors=True,
        include_students=True,
        only_available=True,
    )
    df2 = pd.read_csv(csv_path2)
    # Only two rows remain (both in CS101 course, both available)
    assert len(df2) == 2
    assert set(df2["role"]) == {"Instructor", "Student"}

    # Role filters: exclude students
    csv_path3, _, _ = rg.generate_report(
        data_dir=Path("/does/not/matter"),
        out_dir=tmp_path,
        course_filter=None,
        include_instructors=True,
        include_students=False,
        only_available=True,
    )
    df3 = pd.read_csv(csv_path3)
    assert set(df3["role"]) == {"Instructor"}

    # Role filters: exclude instructors
    csv_path4, _, _ = rg.generate_report(
        data_dir=Path("/does/not/matter"),
        out_dir=tmp_path,
        course_filter=None,
        include_instructors=False,
        include_students=True,
        only_available=True,
    )
    df4 = pd.read_csv(csv_path4)
    assert set(df4["role"]) == {"Student"}

    # Course filter
    csv_path5, _, audit_path5 = rg.generate_report(
        data_dir=Path("/does/not/matter"),
        out_dir=tmp_path,
        course_filter="CS101",
        include_instructors=True,
        include_students=True,
        only_available=True,
    )
    df5 = pd.read_csv(csv_path5)
    assert df5["courseId"].str.contains("CS101").all()

    # Audit keys
    audit = json.loads(audit_path5.read_text())
    assert set(audit.keys()) >= {"timestamp", "args", "input_sizes", "output_sizes", "filters"}

