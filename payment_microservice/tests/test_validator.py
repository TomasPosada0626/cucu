from __future__ import annotations

import pytest

from app.errors import ValidationError
from app.validators.payment_validator import validate_create_payment_payload


def _payload(**overrides):
    payload = {
        "usuario_id": 1,
        "pedido_id": "77",
        "monto": "20000",
        "metodo_pago": "credit_card",
        "moneda": "COP",
    }
    payload.update(overrides)
    return payload


def test_valid_payload_normalizes_fields():
    result = validate_create_payment_payload(_payload())
    assert result["usuario_id"] == 1
    assert result["pedido_id"] == "77"
    assert result["monto"] == 20000.0
    assert result["metodo_pago"] == "credit_card"
    assert result["moneda"] == "COP"


def test_non_dict_payload_raises():
    with pytest.raises(ValidationError):
        validate_create_payment_payload("not-a-dict")


def test_missing_usuario_id_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(usuario_id="abc"))
    assert "usuario_id" in exc_info.value.details


def test_non_positive_usuario_id_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(usuario_id=0))
    assert "usuario_id" in exc_info.value.details


def test_missing_pedido_id_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(pedido_id="  "))
    assert "pedido_id" in exc_info.value.details


def test_invalid_monto_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(monto="no-numero"))
    assert "monto" in exc_info.value.details


def test_non_positive_monto_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(monto="0"))
    assert "monto" in exc_info.value.details


def test_monto_rounds_to_two_decimals():
    result = validate_create_payment_payload(_payload(monto="10.005"))
    assert result["monto"] == 10.01


def test_missing_metodo_pago_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(metodo_pago=""))
    assert "metodo_pago" in exc_info.value.details


def test_non_string_metodo_pago_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(metodo_pago=123))
    assert "metodo_pago" in exc_info.value.details


def test_unsupported_metodo_pago_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(metodo_pago="bitcoin"))
    assert "metodo_pago" in exc_info.value.details


def test_metodo_pago_is_normalized_lowercase():
    result = validate_create_payment_payload(_payload(metodo_pago=" NEQUI "))
    assert result["metodo_pago"] == "nequi"


def test_default_moneda_is_cop_when_omitted():
    payload = _payload()
    del payload["moneda"]
    result = validate_create_payment_payload(payload)
    assert result["moneda"] == "COP"


def test_non_string_moneda_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(moneda=123))
    assert "moneda" in exc_info.value.details


def test_blank_moneda_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(moneda="  "))
    assert "moneda" in exc_info.value.details


def test_unsupported_moneda_collects_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload(_payload(moneda="ARS"))
    assert "moneda" in exc_info.value.details


def test_moneda_is_normalized_uppercase():
    result = validate_create_payment_payload(_payload(moneda="usd"))
    assert result["moneda"] == "USD"


def test_multiple_errors_collected_together():
    with pytest.raises(ValidationError) as exc_info:
        validate_create_payment_payload({})
    details = exc_info.value.details
    assert set(details.keys()) == {"usuario_id", "pedido_id", "monto", "metodo_pago"}
