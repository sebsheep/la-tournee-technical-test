from dataclasses import dataclass
from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import NoResultFound

import app.models as models
from app.core.dispatch import (
    DispatchResponse,
    UnitCountWithPacking,
    to_dispatch_response,
)
from app.core.session import get_session


# Note: the API is supposed to accept something like:
# [{ OrderId: "abc", SKU: "orangina"}, { OrderId: "abc", SKU: "lait"}]
# which could lead to inconsistent OrderId.Hence we should
# check that all the order Ids are the same.
# Instead, the API could accept something like:
# { OrderId: "abc", Products: [{sku: "orangina"}, {sku: "lait"}]}
# which would remove the need
class DispatchRequestItem(BaseModel):
    # I choose to forbid extra arguments in the JSON payload as it may
    # indicate a misconception of the API from the consumer. So forbidden
    # extra arguments will make the server to loudly crash with a clear
    # error message, preventing the consumer hours of errances.
    #
    # Same philosophy with "strict", I don't expect the consumer to
    # learn the pydantic coercion table so I'd like it to be as
    # straightforward as possible.
    model_config = ConfigDict(extra="forbid", strict=True)

    ID: str
    OrderID: str
    SKU: str
    UnitCount: int


@dataclass
class MissingProduct:
    sku: str


async def to_unit_count_with_packing(
    item: DispatchRequestItem, session: AsyncSession
) -> Union[UnitCountWithPacking, MissingProduct]:
    statement = select(models.Product.packing, models.Product.size).where(
        models.Product.sku == item.SKU
    )
    query = await session.execute(statement)

    try:
        packing, size = query.one()
        return UnitCountWithPacking(
            unit_count=item.UnitCount, packing=packing, size=size
        )
    except NoResultFound:
        return MissingProduct(sku=item.SKU)


router = APIRouter()


@router.post("/dispatch", response_model=DispatchResponse)
async def dispatch(
    items: list[DispatchRequestItem],
    session: AsyncSession = Depends(get_session),
):
    results = [await to_unit_count_with_packing(item, session) for item in items]

    validated_items = [r for r in results if type(r) == UnitCountWithPacking]
    if len(validated_items) != len(items):
        missing_skus = [r.sku for r in results if type(r) == MissingProduct]
        raise HTTPException(status_code=404, detail={"non-existing-skus": missing_skus})
    return to_dispatch_response(validated_items)
