from app.errors import ApiError, NotFoundError, ValidationError


def test_api_error_defaults():
    error = ApiError("algo")
    assert error.status_code == 400
    assert error.code == "api_error"
    assert error.details is None


def test_api_error_custom_overrides():
    error = ApiError("x", details={"a": 1}, status_code=418, code="teapot")
    assert error.status_code == 418
    assert error.code == "teapot"
    assert error.details == {"a": 1}


def test_validation_error_defaults():
    error = ValidationError("invalido")
    assert error.status_code == 400
    assert error.code == "validation_error"


def test_not_found_error_defaults():
    error = NotFoundError("no encontrado")
    assert error.status_code == 404
    assert error.code == "not_found"
