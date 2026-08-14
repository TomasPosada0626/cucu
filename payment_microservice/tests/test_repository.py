import pytest

from app.models import Payment
from app.repositories.payment_repository import SQLitePaymentRepository


@pytest.fixture
def repo(tmp_path):
    repository = SQLitePaymentRepository(str(tmp_path / "payments.db"))
    repository.initialize()
    return repository


def _payment(**overrides):
    defaults = dict(
        id="pay-1", pedido_id="77", usuario_id=1, monto=1000.0, moneda="COP",
        metodo_pago="credit_card", estado="PENDIENTE", mensaje_estado="x",
        creado_en="t1", actualizado_en="t1",
    )
    defaults.update(overrides)
    return Payment(**defaults)


def test_create_and_get_by_id(repo):
    repo.create(_payment())
    fetched = repo.get_by_id("pay-1")
    assert fetched is not None
    assert fetched.pedido_id == "77"


def test_get_by_id_not_found_returns_none(repo):
    assert repo.get_by_id("no-existe") is None


def test_update_status_success(repo):
    repo.create(_payment())
    updated = repo.update_status("pay-1", estado="AUTORIZADO", mensaje_estado="ok", actualizado_en="t2")
    assert updated.estado == "AUTORIZADO"
    assert updated.mensaje_estado == "ok"


def test_update_status_nonexistent_returns_none(repo):
    assert repo.update_status("no-existe", estado="X", mensaje_estado="y", actualizado_en="t") is None


def test_initialize_is_idempotent(repo):
    repo.initialize()
    repo.create(_payment(id="pay-2"))
    assert repo.get_by_id("pay-2") is not None
