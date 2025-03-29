from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from itertools import chain
from typing import Any, Generic, Never, TypeVar, cast

from effect.identity import IdentifiedValue, IdentifiedValueSet, Identity
from effect.state_transition import (
    DeadValue,
    MutatedValue,
    NewValue,
    NoValue,
    TranslatedValue,
)


ValueT = TypeVar("ValueT")
NewT = TypeVar("NewT", covariant=True, bound=IdentifiedValue, default=Never)  # noqa: PLC0105
TranslatedT = TypeVar("TranslatedT", covariant=True, bound=IdentifiedValue, default=Never)  # noqa: PLC0105
MutatedT = TypeVar("MutatedT", covariant=True, bound=IdentifiedValue, default=Never)  # noqa: PLC0105
DeadT = TypeVar("DeadT", covariant=True, bound=IdentifiedValue, default=Never)  # noqa: PLC0105
JustT = TypeVar("JustT", default=Never)


@dataclass(frozen=True, slots=True, eq=False)
class Effect(Generic[ValueT, NewT, TranslatedT, MutatedT, DeadT]):
    just: ValueT
    new_values: IdentifiedValueSet[NewT] = IdentifiedValueSet()
    translated_values: IdentifiedValueSet[TranslatedT] = IdentifiedValueSet()
    mutated_values: IdentifiedValueSet[MutatedT] = IdentifiedValueSet()
    dead_values: IdentifiedValueSet[DeadT] = IdentifiedValueSet()

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Effect)
            and self.just == other.just
            and frozenset(self.new_values) == frozenset(other.new_values)
            and frozenset(self.translated_values) == frozenset(other.translated_values)
            and frozenset(self.mutated_values) == frozenset(other.mutated_values)
            and frozenset(self.dead_values) == frozenset(other.dead_values)
        )

    def __hash__(self) -> int:
        return hash(type(self)) + hash(self.just) + hash(tuple(self))

    @classmethod
    def of_values_with_state[
        _ValueT,
        _NewT: IdentifiedValue,
        _TranslatedT: IdentifiedValue,
        _MutatedT: IdentifiedValue,
        _DeadT: IdentifiedValue
    ](
        cls,
        *,
        just: _ValueT,
        values: Iterable[
            NewValue[_NewT]
            | TranslatedValue[_TranslatedT]
            | MutatedValue[_MutatedT]
            | DeadValue[_DeadT]
            | NoValue[Any]
        ]
    ) -> "Effect[_ValueT, _NewT, _TranslatedT, _MutatedT, _DeadT]":
        values = tuple(values)

        return Effect(
            just,
            new_values=IdentifiedValueSet(
                value.just for value in values if isinstance(value, NewValue)
            ),
            translated_values=IdentifiedValueSet(
                value.just for value in values if isinstance(value, TranslatedValue)
            ),
            mutated_values=IdentifiedValueSet(
                value.just for value in values if isinstance(value, MutatedValue)
            ),
            dead_values=IdentifiedValueSet(
                value.just for value in values if isinstance(value, DeadValue)
            ),
        )

    def __iter__(self) -> Iterator[NewT | TranslatedT | MutatedT | DeadT]:
        return iter(
            self.new_values
            | self.translated_values
            | self.mutated_values
            | self.dead_values
        )

    def values_with_state[T](self) -> Iterable[
        NewValue[NewT]
        | TranslatedValue[TranslatedT]
        | MutatedValue[MutatedT]
        | DeadValue[DeadT]
    ]:
        yield from map(NewValue, self.new_values)
        yield from map(TranslatedValue, self.translated_values)
        yield from map(MutatedValue, self.mutated_values)
        yield from map(DeadValue, self.dead_values)

    def value_with_state_by_value[T](
        self,
        value: T
    ) -> (
        NewValue[NewT]
        | TranslatedValue[TranslatedT]
        | MutatedValue[MutatedT]
        | DeadValue[DeadT]
        | NoValue[T]
    ):
        if self.new_values.contains(value):
            return NewValue(value)

        if self.translated_values.contains(value):
            return TranslatedValue(value)

        if self.mutated_values.contains(value):
            return MutatedValue(value)

        if self.dead_values.contains(value):
            return DeadValue(value)

        return NoValue(value)

    def value_with_state_by_identity[T: IdentifiedValue](
        self,
        identity: Identity[T]
    ) -> (
        NewValue[NewT]
        | TranslatedValue[TranslatedT]
        | MutatedValue[MutatedT]
        | DeadValue[DeadT]
        | NoValue[T]
    ):
        for new_value_identity in self.new_values.identities:
            if identity == new_value_identity:
                return NewValue(new_value_identity.value)

        for translated_value_identity in self.translated_values.identities:
            if identity == translated_value_identity:
                return TranslatedValue(translated_value_identity.value)

        for mutated_value_identity in self.mutated_values.identities:
            if identity == mutated_value_identity:
                return MutatedValue(mutated_value_identity.value)

        for dead_value_identity in self.dead_values.identities:
            if identity == dead_value_identity:
                return DeadValue(dead_value_identity.value)

        return NoValue(identity.value)

    def __and__[
        OtherValueT,
        OtherNewT: IdentifiedValue,
        OtherTranslatedT: IdentifiedValue,
        OtherMutatedT: IdentifiedValue,
        OtherDeadT: IdentifiedValue,
    ](
        self,
        right_effect: "Effect[OtherValueT, OtherNewT, OtherTranslatedT, OtherMutatedT, OtherDeadT]",  # noqa: E501
    ) -> "Effect[OtherValueT, NewT | OtherNewT, TranslatedT | OtherTranslatedT, MutatedT | OtherMutatedT, DeadT | OtherDeadT]":  # noqa: E501
        left_values = IdentifiedValueSet(self)
        right_values = IdentifiedValueSet(right_effect)

        left_difference = IdentifiedValueSet(self) - IdentifiedValueSet(right_effect)
        intersection = cast(
            IdentifiedValueSet[
                NewT
                | OtherNewT
                | TranslatedT
                | OtherTranslatedT
                | MutatedT
                | OtherMutatedT
                | DeadT
                | OtherDeadT
            ],
            left_values & right_values,
        )
        right_difference = IdentifiedValueSet(right_effect) - IdentifiedValueSet(self)

        next_intersection_values = (
            (
                self.value_with_state_by_identity(identity)
                & right_effect.value_with_state_by_identity(identity)
            )
            for identity in intersection.identities
        )
        next_left_difference_values = (
            self.value_with_state_by_value(value)
            for value in left_difference
        )
        next_right_difference_values = (
            right_effect.value_with_state_by_value(value)
            for value in right_difference
        )
        next_values = chain(
            next_left_difference_values,
            next_intersection_values,
            next_right_difference_values,
        )

        return Effect.of_values_with_state(
            just=right_effect.just,
            values=next_values,
        )

    def map[ResultT](self, func: Callable[[ValueT], ResultT]) -> (
        "Effect[ResultT, NewT, TranslatedT, MutatedT, DeadT]"
    ):
        return Effect(
            just=func(self.just),
            new_values=self.new_values,
            mutated_values=self.mutated_values,
            dead_values=self.dead_values,
        )

    def and_then[
        OtherValueT,
        OtherNewT: IdentifiedValue,
        OtherTranslatedT: IdentifiedValue,
        OtherMutatedT: IdentifiedValue,
        OtherDeadT: IdentifiedValue,
    ](
        self,
        func: Callable[
            [ValueT],
            "Effect[OtherValueT, OtherNewT, OtherTranslatedT, OtherMutatedT, OtherDeadT]",
        ],
    ) -> "Effect[OtherValueT, NewT | OtherNewT, TranslatedT | OtherTranslatedT, MutatedT | OtherMutatedT, DeadT | OtherDeadT]":  # noqa: E501
        return self & func(self.just)
