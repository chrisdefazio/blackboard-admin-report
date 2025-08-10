import pytest

from scripts.report_generator import (
    AvailabilityBool,
    AvailabilityYesNo,
    Contact,
    Course,
    Enrollment,
    User,
    UserName,
)


def test_valid_models_parse():
    course = Course(
        id="_12345_1",
        courseId="CS101-2025FA",
        name="Intro to CS",
        description="Basics",
        availability=AvailabilityBool(available=True),
    )
    assert course.id == "_12345_1"
    assert course.availability.available is True

    user = User(
        id="_2001_1",
        userName="jdoe",
        name=UserName(given="Jane", family="Doe"),
        contact=Contact(email="jane.doe@example.edu"),
        availability=AvailabilityBool(available=True),
    )
    assert user.contact.email.endswith("@example.edu")

    enrollment = Enrollment(
        id="_30001_1",
        userId="_2001_1",
        courseId="_12345_1",
        type="Student",
        role="Student",
        availability=AvailabilityBool(available=True),
    )
    assert enrollment.availability.available is True


def test_invalid_email_raises_validation_error():
    with pytest.raises(Exception):
        User(
            id="_2001_1",
            userName="jdoe",
            name=UserName(given="Jane", family="Doe"),
            contact=Contact(email="invalid-email"),
            availability=AvailabilityBool(available=True),
        )


def test_unknown_role_logs_warning_but_loads(caplog):
    caplog.clear()
    with caplog.at_level("WARNING"):
        e = Enrollment(
            id="_x_1",
            userId="_u_1",
            courseId="_c_1",
            type="SuperType",
            role="SuperRole",
            availability=AvailabilityBool(available=True),
        )
    assert e.role == "SuperRole"
    # Should log warnings for both type and role
    messages = ",".join(rec.getMessage() for rec in caplog.records)
    assert "Unknown role" in messages or "Unknown type" in messages

