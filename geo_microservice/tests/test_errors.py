from app.errors import ApiError, ValidationError


def test_api_error_defaults():
    error = ApiError("algo")
    assert error.status_code == 400
    assert error.code == "api_error"
    assert error.details is None


def test_api_error_custom_overrides():
    error = ApiError("detalle", details={"a": 1}, status_code=422, code="custom")
    assert error.status_code == 422
    assert error.code == "custom"
    assert error.details == {"a": 1}


def test_validation_error_defaults():
    error = ValidationError("invalido")
    assert error.status_code == 400
    assert error.code == "validation_error"
