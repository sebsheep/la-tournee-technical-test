import math
from dataclasses import dataclass
from functools import reduce
from typing import Optional, Self, Tuple

from pydantic import BaseModel

from app.models import ProductSize

"""
Module containing all the logic to dispatch containers
into crates.
"""


@dataclass
class UnitCountWithPacking:
    unit_count: int
    packing: Optional[int]
    size: ProductSize


class DispatchResponse(BaseModel):
    Supplier: int
    Slot6: int
    Slot12: int
    Slot20: int


@dataclass
class _SupplierCountAndRemainingUnits:
    """This type is the first step of the computation.
    After building a _SupplierCountAndRemainingUnits,
    we know how many supplier crates we need, how many
    products of each kind remain to dispatch in
    our standard crates.

    We can then call `to_dispatch_response` to have the
    (minimal?) number of crates of each kind.
    """

    supplier_count: int
    small_units: int
    big_units: int
    huge_units: int

    @classmethod
    def empty(cls) -> Self:
        return cls(
            supplier_count=0,
            small_units=0,
            big_units=0,
            huge_units=0,
        )

    @classmethod
    def from_unit_count_with_packing(
        cls, unit_count_with_packing: UnitCountWithPacking
    ) -> Self:
        res = cls.empty()
        packing = unit_count_with_packing.packing
        initia_unit_count = unit_count_with_packing.unit_count
        if unit_count_with_packing.packing is None:
            unit_count = initia_unit_count
        else:
            res.supplier_count = initia_unit_count // packing
            unit_count = initia_unit_count % packing

        match unit_count_with_packing.size:
            case ProductSize.SMALL:
                res.small_units = unit_count
            case ProductSize.BIG:
                res.big_units = unit_count
            case ProductSize.TWO_IN_A_BIG:
                # if we have an odd number of those kind of products,
                # we'll have a remaining product once we have made
                # all the pairs of products
                res.big_units = unit_count // 2 + unit_count % 2
            case ProductSize.HUGE:
                res.huge_units = unit_count

        return res

    def merge(self, other: Self) -> Self:
        return _SupplierCountAndRemainingUnits(
            supplier_count=self.supplier_count + other.supplier_count,
            small_units=self.small_units + other.small_units,
            big_units=self.big_units + other.big_units,
            huge_units=self.huge_units + other.huge_units,
        )

    def to_dispatch_response(self) -> DispatchResponse:
        # First we dispatch the big products in crates of 12.
        # If we have more than 6 big products remaining, it means
        # we'll have to fill at least 2 crates of 6 slots, so
        # we're adding 1 crates of 12 slots with some free slots.
        whole_crates_of_12 = self.big_units // 12
        remaining_big = self.big_units % 12
        (crates_of_12, free_slots_last_12, remaining_big) = (
            (whole_crates_of_12 + 1, 12 - remaining_big, 0)
            if remaining_big > 6
            else (whole_crates_of_12, 0, remaining_big)
        )
        assert remaining_big <= 6

        # same logic here for the huge products
        whole_crates_of_10 = self.huge_units // 10
        remaining_huge = self.huge_units % 10
        (crates_of_10, free_slots_last_10, remaining_huge) = (
            (whole_crates_of_10 + 1, 10 - remaining_huge, 0)
            if remaining_huge > 5
            else (whole_crates_of_10, 0, remaining_huge)
        )
        assert remaining_huge <= 5

        # if there are some free slots in the last crate of 12,
        # fill them with huge products (with the rule that
        # as soon as we have a huge product in a crate, we only
        # have 10 slots available, hence the ` - 2`).
        if remaining_huge > 0 and free_slots_last_12 >= 2:
            free_slots_last_12 -= 2
            (remaining_huge, free_slots_last_12) = _transfer(
                remaining_huge, free_slots_last_12
            )

        # if there are some free slots in the last crate of 10,
        # fill them with big_products (this is a "no op" if
        # remaining_big or free_slots_last_10 is 0):
        (remaining_big, free_slots_last_10) = _transfer(
            remaining_big, free_slots_last_10
        )

        # At this point, it remains at most 6 big produts, fitting in at most 1
        # crates of 6 slots
        crates_of_6 = 1 if remaining_big > 0 else 0
        free_slots_last_6 = remaining_big % 6

        # Simalarly for huge products:
        crates_of_5 = 1 if remaining_huge > 0 else 0
        free_slots_last_5 = remaining_huge % 5

        crates_of_20 = self.small_units // 20
        remaining_small = self.small_units % 20

        # We try to dispatch the remaining small products in existing free slots
        # before adding a new crate
        (remaining_small, free_slots_last_12) = _transfer(
            remaining_small, free_slots_last_12
        )

        (remaining_small, free_slots_last_10) = _transfer(
            remaining_small, free_slots_last_10
        )

        (remaining_small, free_slots_last_6) = _transfer(
            remaining_small, free_slots_last_6
        )

        (remaining_small, free_slots_last_5) = _transfer(
            remaining_small, free_slots_last_5
        )

        if remaining_small > 0:
            crates_of_20 += 1

        return DispatchResponse(
            Slot12=crates_of_12 + crates_of_10,
            Slot6=crates_of_6 + crates_of_5,
            Slot20=crates_of_20,
            Supplier=self.supplier_count,
        )


def _transfer(stock: int, free_slots: int) -> Tuple[int, int]:
    moved = min(stock, free_slots)
    return (stock - moved, free_slots - moved)


def to_dispatch_response(items: list[UnitCountWithPacking]) -> DispatchResponse:
    suplier_count_and_remaining_units_list = map(
        _SupplierCountAndRemainingUnits.from_unit_count_with_packing, items
    )

    merged = reduce(
        _SupplierCountAndRemainingUnits.merge,
        suplier_count_and_remaining_units_list,
        _SupplierCountAndRemainingUnits.empty(),
    )
    print(merged)
    return merged.to_dispatch_response()
