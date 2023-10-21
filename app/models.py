"""
SQL Alchemy models declaration.
https://docs.sqlalchemy.org/en/14/orm/declarative_styles.html#example-two-dataclasses-with-declarative-table
Dataclass style for powerful autocompletion support.

https://alembic.sqlalchemy.org/en/latest/tutorial.html
Note, it is used by alembic migrations logic, see `alembic/env.py`

Alembic shortcuts:
# create migration
alembic revision --autogenerate -m "migration_name"

# apply all migrations
alembic upgrade head
"""
import json
from typing import List, Optional
import enum
from pydantic import BaseModel, ConfigDict, RootModel, TypeAdapter

from sqlalchemy import String, Integer, Enum, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.expression import func
import app.core.session


class ProductSize(enum.Enum):
    SMALL = "small"
    BIG = "big"
    HUGE = "huge"
    TWO_IN_A_BIG = "two_in_a_big"


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "product"

    sku: Mapped[str] = mapped_column(String(255), primary_key=True)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    # when  packing is set to `NULL`, we can not use supplier crates
    packing: Mapped[Optional[int]] = mapped_column(Integer())
    size: Mapped[ProductSize] = mapped_column(Enum(ProductSize), nullable=False)


class ProductFromJsonItem(BaseModel):
    """Schema to import the json given in the gist"""

    model_config = ConfigDict(extra="forbid", strict=True)

    sku: str
    brand: str
    packing: int
    deposit: float
    preparation_in_crate: bool

    def consolidated_packing(self) -> Optional[int]:
        if self.brand in ("La Tournée", "Orangina"):
            return None
        if not self.preparation_in_crate:
            return None
        return self.packing

    def size(self) -> ProductSize:
        # special case for orangina: we cannot fit 1 bottle in a small slot
        # but 2
        if self.sku == "orangina-25":
            return ProductSize.TWO_IN_A_BIG
        # special case for La Tournée: all the products are "HUGE"
        if self.brand == "La Tournée":
            return ProductSize.HUGE

        # we take into account 0.2 misrepresentation in base 2
        # BTW, using float for price is kinda dangerous!
        if 0.19 < self.deposit < 0.21:
            return ProductSize.SMALL

        # same here for 0.4
        if 0.39 < self.deposit < 0.41:
            return ProductSize.BIG

        # the json seem a bit buggy, they are a bunch of deposit at 0.
        # For safety, we decide those containers are big.
        if self.deposit == 0:
            return ProductSize.BIG
                
        raise ValueError(
            f"The {self.sku} product has a deposit of {self.deposit} which doesn't fit into the predifined sizing"
        )


async def load_product_from_json():
    with open("store.json", "r") as file:
        raw_content = json.load(file)
    parsed_content = TypeAdapter(List[ProductFromJsonItem]).validate_python(raw_content)
    
    session = app.core.session.async_session()
    
    count_statement = select(func.count()).select_from(Product)
    query =(await session.scalars(count_statement))
    if query.one() > 0:
        print("The product table seems already filled in.")
        return
    
    print("The product table is empty, trying to fill it in!")
    
    for product in parsed_content:
        session.add(
            Product(
                sku=product.sku,
                brand=product.brand,
                packing=product.consolidated_packing(),
                size=product.size(),
            )
        )

    await session.commit()
