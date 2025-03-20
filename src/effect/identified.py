from dataclasses import dataclass
from typing import Any, Self, cast


@dataclass(kw_only=True, frozen=True)
class Identified[IdT = Any]:
    id: IdT

    def is_(self, value: object) -> bool:
        return type(self) is type(value) and self.id == cast(Self, value).id


@dataclass(frozen=True, eq=False, unsafe_hash=False)
class Identity[ValueT: Identified = Identified]:
    value: ValueT

    def __eq__(self, value: object, /) -> bool:
        return self.value.is_(value)

    def __hash__(self) -> int:
        return hash(type(self.value)) + hash(cast(object, self.value.id))
