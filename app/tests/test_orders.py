from httpx import AsyncClient

from app.core.dispatch import (
    DispatchResponse,
    UnitCountWithPacking,
    to_dispatch_response,
)
from app.main import app
from app.models import ProductSize, load_product_from_json


async def test_order_dispatchs_returns_200(client: AsyncClient):
    """This test only ensure the sku request is accepted and is not
    crashing the server.
    """
    # not great, if I had more time, I searched how to add actual fixtures
    await load_product_from_json()
    response = await client.post(
        app.url_path_for("dispatch"),
        json=[
            {
                "ID": "1",
                "OrderID": "abc",
                "SKU": "la-tournee-penne-ble-semi-complet-bio-350",
                "UnitCount": 10,
            }
        ],
    )
    assert response.status_code == 200


def test_dispatch():
    # 1 whole supplier crate + 8 remaining products in 1 slot12
    assert to_dispatch_response(
        [UnitCountWithPacking(unit_count=20, packing=12, size=ProductSize.HUGE)]
    ) == DispatchResponse(Supplier=1, Slot12=1, Slot6=0, Slot20=0)

    # 1  whole slot20, 1 slot6 with 5 big products, 1 slot20 with 6 products
    # Note: we could have optimized this to 1 whole slot20 and 1 slot12 :/
    assert to_dispatch_response(
        [
            UnitCountWithPacking(unit_count=26, packing=None, size=ProductSize.SMALL),
            UnitCountWithPacking(unit_count=5, packing=None, size=ProductSize.BIG),
        ]
    ) == DispatchResponse(Supplier=0, Slot12=0, Slot6=1, Slot20=2)
