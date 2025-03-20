from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import reduce
from itertools import chain
from operator import and_
from typing import Any, Generic, Iterator, Never, Self, TypeVar, cast

from effect.identified import Identified, Identity


class DuplicateError(Exception): ...


class _NoValue: ...


_no_value = _NoValue()


class NoValueError(Exception): ...


ValueT = TypeVar("ValueT")
NewT = TypeVar("NewT", covariant=True, bound=Identified, default=Never)  # noqa: PLC0105
DirtyT = TypeVar("DirtyT", covariant=True, bound=Identified, default=Never)  # noqa: PLC0105
DeletedT = TypeVar("DeletedT", covariant=True, bound=Identified, default=Never)  # noqa: PLC0105
JustT = TypeVar("JustT", default=Never)


class _Effectable(Generic[ValueT, NewT, DirtyT, DeletedT, JustT], ABC):
    @abstractmethod
    def _just(self) -> JustT: ...

    @abstractmethod
    def _as_effect(self) -> "Effect[ValueT, NewT, DirtyT, DeletedT]": ...


@dataclass(kw_only=True, frozen=True, slots=True)
class Effect(
    Generic[ValueT, NewT, DirtyT, DeletedT],
    _Effectable[ValueT, NewT, DirtyT, DeletedT, ValueT]
):
    _value: ValueT
    new_values: tuple[NewT, ...]
    dirty_values: tuple[DirtyT, ...]
    deleted_values: tuple[DeletedT, ...]

    def _as_effect(self) -> Self:
        return self

    def __iter__(self) -> Iterator[NewT | DirtyT | DeletedT]:
        return iter(self.new_values + self.dirty_values + self.deleted_values)

    def __and__[
        OtherValueT,
        OtherNewT: Identified,
        OtherDirtyT: Identified,
        OtherDeletedT: Identified,
    ](
        self,
        other: "_Effectable[OtherValueT, OtherNewT, OtherDirtyT, OtherDeletedT, Any]",  # noqa: E501
    ) -> "Effect[OtherValueT, NewT | OtherNewT, DirtyT | OtherDirtyT, DeletedT | OtherDeletedT]":  # noqa: E501
        other = other._as_effect()

        next_new_values = (
            self._part_of_next_new_values_when(other=cast(AnyEffect, other))
            + other._part_of_next_new_values_when(other=cast(AnyEffect, self))
        )
        next_dirty_values = (
            self._part_of_next_dirty_values_when(other=cast(AnyEffect, other))
            + other._part_of_next_dirty_values_when(other=cast(AnyEffect, self))
        )
        next_deleted_values = self.deleted_values + other.deleted_values

        return Effect(
            _value=other._value,
            new_values=next_new_values,
            dirty_values=next_dirty_values,
            deleted_values=next_deleted_values,
        )

    def _just(self) -> ValueT:
        if self._value is _no_value:
            raise NoValueError

        return self._value

    def _part_of_next_new_values_when(
        self, *, other: "AnyEffect"
    ) -> tuple[NewT, ...]:
        return tuple(
            new_value
            for new_value in self.new_values
            if not other.is_dirty(new_value) and not other.is_deleted(new_value)
        )

    def _part_of_next_dirty_values_when(
        self, *, other: "AnyEffect"
    ) -> tuple[DirtyT, ...]:
        return tuple(
            dirty_value
            for dirty_value in self.dirty_values
            if not other.is_deleted(dirty_value)
        )

    def _filtered_new_values_by(self, other: "AnyEffect") -> tuple[NewT, ...]:
        return tuple(
            new_value
            for new_value in self.new_values
            if not other.is_dirty(new_value) and not other.is_deleted(new_value)
        )

    def is_dirty(self, value: Identified) -> bool:
        return self.__is_in(self.dirty_values, value)

    def is_new(self, value: Identified) -> bool:
        return self.__is_in(self.new_values, value)

    def is_deleted(self, value: Identified) -> bool:
        return self.__is_in(self.deleted_values, value)

    def map[ResultT](self, func: Callable[[ValueT], ResultT]) -> (
        "Effect[ResultT, NewT, DirtyT, DeletedT]"
    ):
        return Effect(
            _value=func(self._value),
            new_values=self.new_values,
            dirty_values=self.dirty_values,
            deleted_values=self.deleted_values,
        )

    def then[
        OtherValueT,
        OtherNewT: Identified,
        OtherDirtyT: Identified,
        OtherDeletedT: Identified,
    ](
        self,
        func: Callable[
            [ValueT],
            "Effect[OtherValueT, OtherNewT, OtherDirtyT, OtherDeletedT]",
        ],
    ) -> "Effect[OtherValueT, NewT | OtherNewT, DirtyT | OtherDirtyT, DeletedT | OtherDeletedT]":  # noqa: E501
        return self & func(self._value)

    def __has_duplicates(self) -> bool:
        all_values = cast(
            Iterable[NewT | DirtyT | DeletedT],
            chain(self.new_values, self.dirty_values, self.deleted_values),
        )
        all_identities = tuple(map(Identity, all_values))
        return len(all_identities) != len(set(all_identities))

    def __post_init__(self) -> None:
        if self.__has_duplicates():
            raise DuplicateError

    def __is_in(
        self, others: tuple[Identified, ...], value: Identified
    ) -> bool:
        return any(value.is_(other) for other in others)


@dataclass(init=False, slots=True)
class _Effects[
    ValueT = _NoValue,
    NewT: Identified = Never,
    DirtyT: Identified = Never,
    DeletedT: Identified = Never,
](_Effectable[ValueT, NewT, DirtyT, DeletedT, tuple[ValueT, ...]]):
    __effects: tuple[Effect[ValueT, NewT, DirtyT, DeletedT], ...]

    def __init__(
        self, effects: Iterable[Effect[ValueT, NewT, DirtyT, DeletedT]]
    ) -> None:
        self.__effects = tuple(effects)

    def _just(self) -> tuple[ValueT, ...]:
        return tuple(
            effect._value  # noqa: SLF001
            for effect in self.__effects
            if effect._value is not _no_value  # noqa: SLF001
        )

    def _as_effect(self) -> Effect[ValueT, NewT, DirtyT, DeletedT]:
        effects = tuple(self.__effects)

        if len(effects) == 0:
            return cast(Effect[ValueT, NewT, DirtyT, DeletedT], Effect(
                _value=_no_value,
                new_values=tuple(),
                dirty_values=tuple(),
                deleted_values=tuple(),
            ))

        return reduce(and_, effects)


type AnyEffect[
    _ValueT = Any,
    _NewT: Identified = Any,
    _DirtyT: Identified = Any,
    _DeletedT: Identified = Any,
] = Effect[_ValueT, _NewT, _DirtyT, _DeletedT]


type LifeCycle[_ValueT: Identified] = Effect[Any, _ValueT, _ValueT, _ValueT]

type Existing[_ValueT: Identified] = Effect[_ValueT, Never, Never, Never]
type New[_ValueT: Identified] = Effect[_ValueT, _ValueT, Never, Never]
type Dirty[_ValueT: Identified] = Effect[_ValueT, Never, _ValueT, Never]
type Deleted[_ValueT: Identified] = Effect[_ValueT, Never, Never, _ValueT]


def just[JustT](value: _Effectable[Any, Any, Any, Any, JustT]) -> JustT:
    return value._just()  # noqa: SLF001


def many[
    _ValueT, _NewT: Identified, _DirtyT: Identified, _DeletedT: Identified
](
    effects: Iterable[Effect[_ValueT, _NewT, _DirtyT, _DeletedT]]
) -> _Effects[_ValueT, _NewT, _DirtyT, _DeletedT]:
    return _Effects(effects)


def existing[_ValueT: Identified](value: _ValueT) -> Existing[_ValueT]:
    return Effect(
        _value=value,
        new_values=tuple(),
        dirty_values=tuple(),
        deleted_values=tuple(),
    )


def new[_ValueT: Identified](value: _ValueT) -> New[_ValueT]:
    return Effect(
        _value=value,
        new_values=(value, ),
        dirty_values=tuple(),
        deleted_values=tuple(),
    )


def dirty[_ValueT: Identified](value: _ValueT) -> Dirty[_ValueT]:
    return Effect(
        _value=value,
        new_values=tuple(),
        dirty_values=(value, ),
        deleted_values=tuple(),
    )


def deleted[ValueT: Identified](value: ValueT) -> Deleted[ValueT]:
    return Effect(
        _value=value,
        new_values=tuple(),
        dirty_values=tuple(),
        deleted_values=(value, ),
    )
