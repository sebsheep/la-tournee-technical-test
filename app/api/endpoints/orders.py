from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict


# For bigger projects, I saw that the FastAPI convention was to
# have a specific `schema` module, but for this simple one-route
# project, I think having all the info about routes in one place
# is more convenient.

class DispatchResponse(BaseModel):
    Supplier: int
    Slot6: int
    Slot12: int
    Slot20: int


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


router = APIRouter()


@router.post("/dispatch", response_model=DispatchResponse)
def dispatch(items: list[DispatchRequestItem]):
    return DispatchResponse(
        Supplier=sum(item.UnitCount for item in items), Slot6=1, Slot12=0, Slot20=0
    )
