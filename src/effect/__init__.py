from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from functools import reduce
from itertools import chain
from operator import and_
from typing import Any, Generic, Never, Self, TypeVar, cast


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


class DuplicateError(Exception): ...


class _NoValue: ...


_no_value = _NoValue()


class NoValueError(Exception): ...


ValueT = TypeVar("ValueT")
NewT = TypeVar("NewT", covariant=True, bound=Identified, default=Never)  # noqa: PLC0105
MutatedT = TypeVar("MutatedT", covariant=True, bound=Identified, default=Never)  # noqa: PLC0105
DeletedT = TypeVar("DeletedT", covariant=True, bound=Identified, default=Never)  # noqa: PLC0105
JustT = TypeVar("JustT", default=Never)


class _Effectable(
    Generic[ValueT, NewT, MutatedT, DeletedT, JustT],
    Iterable[NewT | MutatedT | DeletedT],
    ABC,
):
    @abstractmethod
    def _just(self) -> JustT: ...

    @abstractmethod
    def _as_effect(self) -> "Effect[ValueT, NewT, MutatedT, DeletedT]": ...


@dataclass(kw_only=True, frozen=True, slots=True)
class Effect(
    Generic[ValueT, NewT, MutatedT, DeletedT],
    _Effectable[ValueT, NewT, MutatedT, DeletedT, ValueT]
):
    _value: ValueT
    new_values: tuple[NewT, ...]
    mutated_values: tuple[MutatedT, ...]
    deleted_values: tuple[DeletedT, ...]

    def _as_effect(self) -> Self:
        return self

    def __iter__(self) -> Iterator[NewT | MutatedT | DeletedT]:
        return iter(self.new_values + self.mutated_values + self.deleted_values)

    def __and__[
        OtherValueT,
        OtherNewT: Identified,
        OtherMutatedT: Identified,
        OtherDeletedT: Identified,
    ](
        self,
        other: "_Effectable[OtherValueT, OtherNewT, OtherMutatedT, OtherDeletedT, Any]",
    ) -> "Effect[OtherValueT, NewT | OtherNewT, MutatedT | OtherMutatedT, DeletedT | OtherDeletedT]":  # noqa: E501
        other = other._as_effect()

        next_new_values = (
            self._part_of_next_new_values_when(other=cast(AnyEffect, other))
            + other._part_of_next_new_values_when(other=cast(AnyEffect, self))
        )
        next_mutated_values = (
            self._part_of_next_mutated_values_when(other=cast(AnyEffect, other))
            + other._part_of_next_mutated_values_when(other=cast(AnyEffect, self))
        )
        next_deleted_values = self.deleted_values + other.deleted_values

        return Effect(
            _value=other._value,
            new_values=next_new_values,
            mutated_values=next_mutated_values,
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
            if not other.is_mutated(new_value) and not other.is_deleted(new_value)
        )

    def _part_of_next_mutated_values_when(
        self, *, other: "AnyEffect"
    ) -> tuple[MutatedT, ...]:
        return tuple(
            mutated_value
            for mutated_value in self.mutated_values
            if not other.is_deleted(mutated_value)
        )

    def _filtered_new_values_by(self, other: "AnyEffect") -> tuple[NewT, ...]:
        return tuple(
            new_value
            for new_value in self.new_values
            if not other.is_mutated(new_value) and not other.is_deleted(new_value)
        )

    def is_mutated(self, value: Identified) -> bool:
        return self.__is_in(self.mutated_values, value)

    def is_new(self, value: Identified) -> bool:
        return self.__is_in(self.new_values, value)

    def is_deleted(self, value: Identified) -> bool:
        return self.__is_in(self.deleted_values, value)

    def map[ResultT](self, func: Callable[[ValueT], ResultT]) -> (
        "Effect[ResultT, NewT, MutatedT, DeletedT]"
    ):
        return Effect(
            _value=func(self._value),
            new_values=self.new_values,
            mutated_values=self.mutated_values,
            deleted_values=self.deleted_values,
        )

    def then[
        OtherValueT,
        OtherNewT: Identified,
        OtherMutatedT: Identified,
        OtherDeletedT: Identified,
    ](
        self,
        func: Callable[
            [ValueT],
            "Effect[OtherValueT, OtherNewT, OtherMutatedT, OtherDeletedT]",
        ],
    ) -> "Effect[OtherValueT, NewT | OtherNewT, MutatedT | OtherMutatedT, DeletedT | OtherDeletedT]":  # noqa: E501
        return self & func(self._value)

    def __has_duplicates(self) -> bool:
        all_values = cast(
            Iterable[NewT | MutatedT | DeletedT],
            chain(self.new_values, self.mutated_values, self.deleted_values),
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
    MutatedT: Identified = Never,
    DeletedT: Identified = Never,
](_Effectable[ValueT, NewT, MutatedT, DeletedT, tuple[ValueT, ...]]):
    _effects: tuple[Effect[ValueT, NewT, MutatedT, DeletedT], ...]

    @property
    def new_values(self) -> tuple[NewT, ...]:
        new_values = chain.from_iterable(
            effect.new_values for effect in self._effects
        )
        return tuple(new_values)

    @property
    def mutated_values(self) -> tuple[MutatedT, ...]:
        mutated_values = chain.from_iterable(
            effect.mutated_values for effect in self._effects
        )
        return tuple(mutated_values)

    @property
    def deleted_values(self) -> tuple[DeletedT, ...]:
        deleted_values = chain.from_iterable(
            effect.deleted_values for effect in self._effects
        )
        return tuple(deleted_values)

    def __init__(
        self, effects: Iterable[Effect[ValueT, NewT, MutatedT, DeletedT]]
    ) -> None:
        self._effects = tuple(effects)

    def __iter__(self) -> Iterator[NewT | MutatedT | DeletedT]:
        return chain.from_iterable(map(iter, self._effects))

    def _just(self) -> tuple[ValueT, ...]:
        return tuple(
            effect._value  # noqa: SLF001
            for effect in self._effects
            if effect._value is not _no_value  # noqa: SLF001
        )

    def _as_effect(self) -> Effect[ValueT, NewT, MutatedT, DeletedT]:
        effects = tuple(self._effects)

        if len(effects) == 0:
            return cast(Effect[ValueT, NewT, MutatedT, DeletedT], Effect(
                _value=_no_value,
                new_values=tuple(),
                mutated_values=tuple(),
                deleted_values=tuple(),
            ))

        return reduce(and_, effects)


type AnyEffect[
    _ValueT = Any,
    _NewT: Identified = Any,
    _MutatedT: Identified = Any,
    _DeletedT: Identified = Any,
] = Effect[_ValueT, _NewT, _MutatedT, _DeletedT]

type Many[
    _ValueT = Any,
    _NewT: Identified = Any,
    _MutatedT: Identified = Any,
    _DeletedT: Identified = Any,
] = _Effects[_ValueT, _NewT, _MutatedT, _DeletedT]


type LifeCycle[_ValueT: Identified] = Effect[Any, _ValueT, _ValueT, _ValueT]

type Existing[_ValueT: Identified] = Effect[_ValueT, Never, Never, Never]
type New[_ValueT: Identified] = Effect[_ValueT, _ValueT, Never, Never]
type Mutated[_ValueT: Identified] = Effect[_ValueT, Never, _ValueT, Never]
type Deleted[_ValueT: Identified] = Effect[_ValueT, Never, Never, _ValueT]


def just[JustT](value: _Effectable[Any, Any, Any, Any, JustT]) -> JustT:
    return value._just()  # noqa: SLF001


def many[
    _ValueT, _NewT: Identified, _MutatedT: Identified, _DeletedT: Identified
](
    effects: Iterable[Effect[_ValueT, _NewT, _MutatedT, _DeletedT]]
) -> _Effects[_ValueT, _NewT, _MutatedT, _DeletedT]:
    return _Effects(effects)


def existing[_ValueT: Identified](value: _ValueT) -> Existing[_ValueT]:
    return Effect(
        _value=value,
        new_values=tuple(),
        mutated_values=tuple(),
        deleted_values=tuple(),
    )


def new[_ValueT: Identified](value: _ValueT) -> New[_ValueT]:
    return Effect(
        _value=value,
        new_values=(value, ),
        mutated_values=tuple(),
        deleted_values=tuple(),
    )


def mutated[_ValueT: Identified](value: _ValueT) -> Mutated[_ValueT]:
    return Effect(
        _value=value,
        new_values=tuple(),
        mutated_values=(value, ),
        deleted_values=tuple(),
    )


def deleted[ValueT: Identified](value: ValueT) -> Deleted[ValueT]:
    return Effect(
        _value=value,
        new_values=tuple(),
        mutated_values=tuple(),
        deleted_values=(value, ),
    )
