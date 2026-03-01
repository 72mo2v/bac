import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.modules.auth.models import StoreUser, User, UserRole
from app.modules.couriers.models import Courier, CourierStatus
from app.modules.orders.models import (
    Order,
    OrderHistory,
    OrderStatus,
    ReturnRequest,
    ReturnStatus,
    CourierReturnStatus,
)
from app.modules.stores.models import Store, StoreVerificationStatus
from app.modules.auth.models import UserAccessStatus
from app.modules.notifications.models import PushToken, Notification
from app.modules.notifications.services.notification_service import NotificationService
from sqlalchemy import select, text
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_assign_courier_moves_to_ready_and_generates_qr(db_session):
    store = Store(
        name="S1",
        slug="s1",
        verification_status=StoreVerificationStatus.APPROVED,
        is_active=True,
    )
    merchant = User(email="m1@example.com", hashed_password="x", role=UserRole.STORE_OWNER, is_active=True)
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, merchant, courier_user, customer])
    await db_session.flush()

    db_session.add(StoreUser(user_id=merchant.id, store_id=store.id, role=UserRole.STORE_OWNER))
    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))
    db_session.add(
        Courier(
            user_id=courier_user.id,
            store_id=store.id,
            status=CourierStatus.ACTIVE,
            vehicle_type="bike",
            license_plate="X",
            is_available=True,
            courier_code="CR-S1-1",
        )
    )
    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        status=OrderStatus.PREPARING,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return merchant

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/orders/{order.id}/assign-courier",
            headers={"X-Store-ID": str(store.id)},
            json={"courier_user_id": courier_user.id},
        )

    app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["courier_id"] == courier_user.id
    assert data["status"] == "READY"
    assert not data.get("delivery_qr_code")


@pytest.mark.asyncio
async def test_assign_courier_rejects_courier_from_other_store(db_session):
    store1 = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    store2 = Store(name="S2", slug="s2", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    merchant = User(email="m1@example.com", hashed_password="x", role=UserRole.STORE_OWNER, is_active=True)
    courier_user = User(email="c2@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store1, store2, merchant, courier_user, customer])
    await db_session.flush()

    db_session.add(StoreUser(user_id=merchant.id, store_id=store1.id, role=UserRole.STORE_OWNER))
    db_session.add(StoreUser(user_id=courier_user.id, store_id=store2.id, role=UserRole.COURIER))
    db_session.add(
        Courier(
            user_id=courier_user.id,
            store_id=store2.id,
            status=CourierStatus.ACTIVE,
            vehicle_type="bike",
            license_plate="X",
            is_available=True,
            courier_code="CR-S2-1",
        )
    )
    order = Order(
        store_id=store1.id,
        customer_id=customer.id,
        status=OrderStatus.PREPARING,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return merchant

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/orders/{order.id}/assign-courier",
            headers={"X-Store-ID": str(store1.id)},
            json={"courier_user_id": courier_user.id},
        )

    app.dependency_overrides.clear()

    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_courier_start_moves_ready_to_out_for_delivery(db_session):
    store = Store(
        name="S1",
        slug="s1",
        verification_status=StoreVerificationStatus.APPROVED,
        is_active=True,
    )
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, courier_user, customer])
    await db_session.flush()

    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))
    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.READY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return courier_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/orders/{order.id}/courier/start")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "OUT_FOR_DELIVERY"
        assert data.get("delivery_qr_code")

        # Ensure persisted and visible on a follow-up read.
        resp2 = await client.get(f"/api/v1/orders/{order.id}")
        assert resp2.status_code == 200, resp2.text
        data2 = resp2.json()
        assert data2["status"] == "OUT_FOR_DELIVERY"
        assert data2.get("delivery_qr_code")

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_courier_confirm_delivered_by_qr_succeeds(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, courier_user, customer])
    await db_session.flush()

    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))
    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.OUT_FOR_DELIVERY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
        delivery_confirm_code="test-code",
        delivery_qr_code="data:image/png;base64,xxx",
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return courier_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        qr_data = f"DELIVERY-{order.id}-{store.id}-test-code"
        resp = await client.post("/api/v1/orders/courier/confirm-delivered", json={"qr_data": qr_data})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "DELIVERED"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_courier_confirm_delivered_by_qr_rejects_wrong_courier(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    other_courier = User(email="c2@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, courier_user, other_courier, customer])
    await db_session.flush()

    db_session.add_all(
        [
            StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER),
            StoreUser(user_id=other_courier.id, store_id=store.id, role=UserRole.COURIER),
        ]
    )
    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.OUT_FOR_DELIVERY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
        delivery_confirm_code="test-code",
        delivery_qr_code="data:image/png;base64,xxx",
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return other_courier

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        qr_data = f"DELIVERY-{order.id}-{store.id}-test-code"
        resp = await client.post("/api/v1/orders/courier/confirm-delivered", json={"qr_data": qr_data})
        assert resp.status_code == 403, resp.text

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_courier_confirm_delivered_by_qr_rejects_wrong_code(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, courier_user, customer])
    await db_session.flush()

    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))
    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.OUT_FOR_DELIVERY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
        delivery_confirm_code="real-code",
        delivery_qr_code="data:image/png;base64,xxx",
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return courier_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        qr_data = f"DELIVERY-{order.id}-{store.id}-wrong-code"
        resp = await client.post("/api/v1/orders/courier/confirm-delivered", json={"qr_data": qr_data})
        assert resp.status_code == 400, resp.text

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_customer_list_orders_includes_courier_info(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    courier_user = User(
        email="c1@example.com",
        hashed_password="x",
        role=UserRole.COURIER,
        is_active=True,
        full_name="Courier One",
        phone_number="+201000000000",
    )
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, courier_user, customer])
    await db_session.flush()

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.OUT_FOR_DELIVERY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
        delivery_confirm_code="test-code",
        delivery_qr_code="data:image/png;base64,xxx",
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return customer

    app.dependency_overrides[get_db] = _override_get_db
    # list_orders uses get_current_user (not get_current_active_user).
    from app.core.deps import get_current_user
    app.dependency_overrides[get_current_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/orders/")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list) and len(data) == 1
        assert data[0]["id"] == order.id
        assert data[0].get("courier") is not None
        assert data[0]["courier"]["full_name"] == "Courier One"
        assert data[0]["courier"]["phone_number"] == "+201000000000"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_couriers_scoped_to_store(db_session):
    store1 = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    store2 = Store(name="S2", slug="s2", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    merchant = User(email="m1@example.com", hashed_password="x", role=UserRole.STORE_OWNER, is_active=True)
    c1u = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    c2u = User(email="c2@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    db_session.add_all([store1, store2, merchant, c1u, c2u])
    await db_session.flush()

    db_session.add(StoreUser(user_id=merchant.id, store_id=store1.id, role=UserRole.STORE_OWNER))
    db_session.add(StoreUser(user_id=c1u.id, store_id=store1.id, role=UserRole.COURIER))
    db_session.add(StoreUser(user_id=c2u.id, store_id=store2.id, role=UserRole.COURIER))
    db_session.add_all(
        [
            Courier(
                user_id=c1u.id,
                store_id=store1.id,
                status=CourierStatus.ACTIVE,
                vehicle_type="bike",
                license_plate="X",
                is_available=True,
                courier_code="CR-S1-1",
            ),
            Courier(
                user_id=c2u.id,
                store_id=store2.id,
                status=CourierStatus.ACTIVE,
                vehicle_type="bike",
                license_plate="Y",
                is_available=True,
                courier_code="CR-S2-1",
            ),
        ]
    )
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return merchant

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/couriers", headers={"X-Store-ID": str(store1.id)})

    app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert {x["store_id"] for x in data} == {store1.id}


@pytest.mark.asyncio
async def test_customer_confirm_delivered_updates_status(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    db_session.add_all([store, customer, courier_user])
    await db_session.flush()

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.OUT_FOR_DELIVERY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return customer

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/orders/{order.id}/customer/confirm-delivered")

    app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "DELIVERED"


@pytest.mark.asyncio
async def test_customer_confirm_delivered_succeeds_if_notification_db_fails(db_session, monkeypatch):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True)
    db_session.add_all([store, customer, courier_user])
    await db_session.flush()

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.OUT_FOR_DELIVERY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return customer

    async def _failing_notify_user(self, *args, **kwargs):
        # Simulate a real database error (would abort the transaction without a SAVEPOINT).
        await self.notification_repo.db.execute(text("SELECT 1/0"))

    monkeypatch.setattr(NotificationService, "notify_user", _failing_notify_user)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/orders/{order.id}/customer/confirm-delivered")

    app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "DELIVERED"


@pytest.mark.asyncio
async def test_create_return_request_rejects_after_3_days_from_delivered(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, customer])
    await db_session.flush()

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        status=OrderStatus.DELIVERED,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.flush()

    delivered_at = datetime.utcnow() - timedelta(days=4)
    db_session.add(
        OrderHistory(
            order_id=order.id,
            status_from=OrderStatus.OUT_FOR_DELIVERY,
            status_to=OrderStatus.DELIVERED,
            changed_by_id=customer.id,
            note="delivered",
            created_at=delivered_at,
        )
    )
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return customer

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/orders/{order.id}/returns", json={"reason": "x", "notes": "y"})

    app.dependency_overrides.clear()
    assert resp.status_code == 400, resp.text
    assert "Return window expired" in resp.text


@pytest.mark.asyncio
async def test_create_return_request_allows_within_3_days_from_delivered(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, customer])
    await db_session.flush()

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        status=OrderStatus.DELIVERED,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.flush()

    delivered_at = datetime.utcnow() - timedelta(days=2)
    db_session.add(
        OrderHistory(
            order_id=order.id,
            status_from=OrderStatus.OUT_FOR_DELIVERY,
            status_to=OrderStatus.DELIVERED,
            changed_by_id=customer.id,
            note="delivered",
            created_at=delivered_at,
        )
    )
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return customer

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/orders/{order.id}/returns", json={"reason": "x", "notes": "y"})

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["order_id"] == order.id
    assert body["status"] == "PENDING"


@pytest.mark.asyncio
async def test_assign_return_courier_requires_approved(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    merchant = User(email="m1@example.com", hashed_password="x", role=UserRole.STORE_OWNER, is_active=True)
    courier_user = User(
        email="c1@example.com",
        hashed_password="x",
        role=UserRole.COURIER,
        is_active=True,
        access_status=UserAccessStatus.ACTIVE,
    )
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, merchant, courier_user, customer])
    await db_session.flush()
    db_session.add(StoreUser(user_id=merchant.id, store_id=store.id, role=UserRole.STORE_OWNER))
    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        status=OrderStatus.DELIVERED,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.flush()

    rr = ReturnRequest(
        store_id=store.id,
        order_id=order.id,
        customer_id=customer.id,
        status=ReturnStatus.PENDING,
    )
    db_session.add(rr)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return merchant

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/orders/returns/{rr.id}/assign-courier",
            headers={"X-Store-ID": str(store.id)},
            json={"courier_user_id": courier_user.id},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_assign_return_courier_sets_assigned(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    merchant = User(email="m1@example.com", hashed_password="x", role=UserRole.STORE_OWNER, is_active=True)
    courier_user = User(
        email="c1@example.com",
        hashed_password="x",
        role=UserRole.COURIER,
        is_active=True,
        access_status=UserAccessStatus.ACTIVE,
    )
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, merchant, courier_user, customer])
    await db_session.flush()
    db_session.add(StoreUser(user_id=merchant.id, store_id=store.id, role=UserRole.STORE_OWNER))
    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        status=OrderStatus.DELIVERED,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.flush()

    rr = ReturnRequest(
        store_id=store.id,
        order_id=order.id,
        customer_id=customer.id,
        status=ReturnStatus.APPROVED,
    )
    db_session.add(rr)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return merchant

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/orders/returns/{rr.id}/assign-courier",
            headers={"X-Store-ID": str(store.id)},
            json={"courier_user_id": courier_user.id},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["courier_user_id"] == courier_user.id
    assert body["courier_status"] == CourierReturnStatus.ASSIGNED.value


@pytest.mark.asyncio
async def test_create_payment_ignores_store_header_scope(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, customer])
    await db_session.flush()

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        status=OrderStatus.PENDING,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/payments/",
            headers={"X-Store-ID": "999999"},
            json={"order_id": int(order.id), "method": "CASH_ON_DELIVERY"},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["order_id"] == int(order.id)


@pytest.mark.asyncio
async def test_courier_start_updates_status_to_out_for_delivery(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    courier_user = User(
        email="c1@example.com",
        hashed_password="x",
        role=UserRole.COURIER,
        is_active=True,
        access_status=UserAccessStatus.ACTIVE,
    )
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, courier_user, customer])
    await db_session.flush()

    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.READY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return courier_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/orders/{order.id}/courier/start")

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == OrderStatus.OUT_FOR_DELIVERY.value

    res = await db_session.execute(select(Order).where(Order.id == int(order.id)))
    db_order = res.scalar_one()
    assert db_order.status == OrderStatus.OUT_FOR_DELIVERY


@pytest.mark.asyncio
async def test_courier_admin_action_activate_and_block(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    merchant = User(email="m1@example.com", hashed_password="x", role=UserRole.STORE_OWNER, is_active=True)
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True, access_status=UserAccessStatus.ACTIVE)
    db_session.add_all([store, merchant, courier_user])
    await db_session.flush()

    db_session.add(StoreUser(user_id=merchant.id, store_id=store.id, role=UserRole.STORE_OWNER))
    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))
    courier = Courier(
        user_id=courier_user.id,
        store_id=store.id,
        status=CourierStatus.PENDING,
        vehicle_type="bike",
        license_plate="X",
        is_available=False,
        courier_code="CR-S1-1",
    )
    db_session.add(courier)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return merchant

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/couriers/{courier.id}/admin-action",
            headers={"X-Store-ID": str(store.id)},
            json={"action": "ACTIVATE"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "ACTIVE"
        assert data["is_available"] is True
        assert (data.get("user") or {}).get("access_status") == "ACTIVE"

        resp2 = await client.post(
            f"/api/v1/couriers/{courier.id}/admin-action",
            headers={"X-Store-ID": str(store.id)},
            json={"action": "BLOCK"},
        )
        assert resp2.status_code == 200, resp2.text
        data2 = resp2.json()
        assert data2["status"] == "INACTIVE"
        assert (data2.get("user") or {}).get("access_status") == "BLOCKED"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assign_courier_rejects_blocked_account(db_session):
    store = Store(name="S1", slug="s1", verification_status=StoreVerificationStatus.APPROVED, is_active=True)
    merchant = User(email="m1@example.com", hashed_password="x", role=UserRole.STORE_OWNER, is_active=True)
    courier_user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True, access_status=UserAccessStatus.BLOCKED)
    customer = User(email="u1@example.com", hashed_password="x", role=UserRole.CUSTOMER, is_active=True)
    db_session.add_all([store, merchant, courier_user, customer])
    await db_session.flush()

    db_session.add(StoreUser(user_id=merchant.id, store_id=store.id, role=UserRole.STORE_OWNER))
    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))
    db_session.add(
        Courier(
            user_id=courier_user.id,
            store_id=store.id,
            status=CourierStatus.ACTIVE,
            vehicle_type="bike",
            license_plate="X",
            is_available=True,
            courier_code="CR-S1-1",
        )
    )
    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        status=OrderStatus.PREPARING,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return merchant

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/orders/{order.id}/assign-courier",
            headers={"X-Store-ID": str(store.id)},
            json={"courier_user_id": courier_user.id},
        )

    app.dependency_overrides.clear()

    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_push_token_register(db_session):
    user = User(email="c1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True, access_status=UserAccessStatus.ACTIVE)
    db_session.add(user)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/notifications/push-tokens/register",
            json={"token": "test-token", "platform": "ANDROID"},
        )
        assert resp.status_code == 200, resp.text

    app.dependency_overrides.clear()

    res = await db_session.execute(select(PushToken).where(PushToken.user_id == user.id))
    row = res.scalar_one_or_none()
    assert row is not None
    assert row.token == "test-token"


@pytest.mark.asyncio
async def test_notifications_mark_one_read(db_session):
    user = User(email="n1@example.com", hashed_password="x", role=UserRole.COURIER, is_active=True, access_status=UserAccessStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()

    notif = Notification(
        user_id=user.id,
        title="T",
        message="M",
        type="order",
        data={"order_id": 1},
        is_read=False,
    )
    db_session.add(notif)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/notifications/{notif.id}/mark-read")
        assert resp.status_code == 200, resp.text
        assert resp.json().get("updated") == 1

    app.dependency_overrides.clear()

    res = await db_session.execute(select(Notification).where(Notification.id == notif.id))
    updated = res.scalar_one()
    assert updated.is_read is True


@pytest.mark.asyncio
async def test_order_customer_includes_phone_number(db_session):
    store = Store(
        name="S1",
        slug="s1",
        verification_status=StoreVerificationStatus.APPROVED,
        is_active=True,
    )
    courier_user = User(
        email="c1@example.com",
        hashed_password="x",
        role=UserRole.COURIER,
        is_active=True,
        access_status=UserAccessStatus.ACTIVE,
    )
    customer = User(
        email="u1@example.com",
        hashed_password="x",
        role=UserRole.CUSTOMER,
        is_active=True,
        phone_number="01000000000",
    )
    db_session.add_all([store, courier_user, customer])
    await db_session.flush()

    db_session.add(StoreUser(user_id=courier_user.id, store_id=store.id, role=UserRole.COURIER))
    db_session.add(
        Courier(
            user_id=courier_user.id,
            store_id=store.id,
            status=CourierStatus.ACTIVE,
            vehicle_type="bike",
            license_plate="X",
            is_available=True,
            courier_code="CR-S1-1",
        )
    )
    order = Order(
        store_id=store.id,
        customer_id=customer.id,
        courier_id=courier_user.id,
        status=OrderStatus.OUT_FOR_DELIVERY,
        total_amount=10.0,
        shipping_address="addr",
        is_paid=False,
    )
    db_session.add(order)
    await db_session.commit()

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return courier_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/orders/{order.id}")

    app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["customer"]["phone_number"] == "01000000000"
