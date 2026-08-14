from app.errors import ApiError, ConflictError, NotFoundError, ValidationError


def test_api_error_defaults():
    error = ApiError("x")
    assert error.status_code == 400
    assert error.code == "api_error"


def test_api_error_custom_overrides():
    error = ApiError("x", details={"a": 1}, status_code=418, code="teapot")
    assert error.status_code == 418
    assert error.code == "teapot"
    assert error.details == {"a": 1}


def test_validation_error_defaults():
    assert ValidationError("x").status_code == 400


def test_not_found_error_defaults():
    assert NotFoundError("x").status_code == 404


def test_conflict_error_defaults():
    assert ConflictError("x").status_code == 409
