from app.errors import ApiError, ConflictError, NotFoundError, UnauthorizedError, ValidationError


def test_api_error_defaults():
    error = ApiError("algo salio mal")
    assert error.status_code == 400
    assert error.code == "api_error"
    assert error.message == "algo salio mal"
    assert error.details is None


def test_api_error_custom_overrides():
    error = ApiError("detalle", details={"field": "x"}, status_code=418, code="teapot")
    assert error.status_code == 418
    assert error.code == "teapot"
    assert error.details == {"field": "x"}


def test_validation_error_defaults():
    error = ValidationError("invalido")
    assert error.status_code == 400
    assert error.code == "validation_error"


def test_unauthorized_error_defaults():
    error = UnauthorizedError("no autorizado")
    assert error.status_code == 401
    assert error.code == "unauthorized"


def test_not_found_error_defaults():
    error = NotFoundError("no encontrado")
    assert error.status_code == 404
    assert error.code == "not_found"


def test_conflict_error_defaults():
    error = ConflictError("conflicto")
    assert error.status_code == 409
    assert error.code == "conflict"
