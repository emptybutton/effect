from collections.abc import Iterable, Iterator, Set
from dataclasses import dataclass
from typing import Any, Self, TypeGuard, cast


@dataclass(frozen=True)
class IdentifiedValue[IdT = Any]:
    id: IdT

    def is_(self, value: object) -> bool:
        return type(self) is type(value) and self.id == cast(Self, value).id

    def is_in(self, values: Iterable[object]) -> bool:
        return any(self.is_(value) for value in values)


@dataclass(frozen=True, eq=False, unsafe_hash=False)
class Identity[ValueT: IdentifiedValue = IdentifiedValue]:
    value: ValueT

    def __eq__(self, identity: object, /) -> bool:
        return (
            type(identity) is type(self)
            and self.value.is_(cast(Self, identity).value)
        )

    def __hash__(self) -> int:
        return hash(type(self.value)) + hash(cast(object, self.value.id))


@dataclass(slots=True, init=False, unsafe_hash=True, repr=False)
class IdentifiedValueSet[IdentifiedT: IdentifiedValue](Set[IdentifiedT]):
    _identities: frozenset[Identity[IdentifiedT]]

    def __init__(self, values: Iterable[IdentifiedT] = tuple()) -> None:
        self._identities = frozenset({Identity(value) for value in values})

    @property
    def identities(self) -> frozenset[Identity[IdentifiedT]]:
        return self._identities

    def __repr__(self) -> str:
        return f"{type(self).__name__}{tuple(self)}"

    def contains(self, value: object) -> TypeGuard[IdentifiedT]:
        return value in self

    def __contains__(self, value: object) -> TypeGuard[IdentifiedT]:
        return isinstance(value, IdentifiedValue) and Identity(value) in self._identities

    def __iter__(self) -> Iterator[IdentifiedT]:
        return (identity.value for identity in self._identities)

    def __len__(self) -> int:
        return len(self._identities)
