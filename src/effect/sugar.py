from collections.abc import Iterable
from functools import reduce
from typing import Any, Never

from effect.effect import DeadT, Effect, MutatedT, NewT, TranslatedT, ValueT
from effect.identity import IdentifiedValue, IdentifiedValueSet
from effect.state_transition import ValueWithState


type AnyEffect[
    _ValueT = Any,
    _NewT: IdentifiedValue = Any,
    _TranslatedT: IdentifiedValue = Any,
    _MutatedT: IdentifiedValue = Any,
    _DeadT: IdentifiedValue = Any,
] = Effect[_ValueT, _NewT, _TranslatedT, _MutatedT, _DeadT]


type LifeCycle[_ValueT: IdentifiedValue] = Effect[Any, _ValueT, _ValueT, _ValueT, _ValueT]

type Existing[_ValueT: IdentifiedValue] = Effect[_ValueT, Never, Never, Never, Never]
type New[_ValueT: IdentifiedValue] = Effect[_ValueT, _ValueT, Never, Never, Never]
type Translated[_ValueT: IdentifiedValue] = Effect[_ValueT, Never, _ValueT, Never, Never]
type Mutated[_ValueT: IdentifiedValue] = Effect[_ValueT, Never, Never, _ValueT, Never]
type Dead[_ValueT: IdentifiedValue] = Effect[_ValueT, Never, Never, Never, _ValueT]


def just[JustT](value: AnyEffect[JustT] | ValueWithState[JustT]) -> JustT:
    return value.just


def many(
    effects: Iterable[Effect[ValueT, NewT, TranslatedT, MutatedT, DeadT]]
) -> Effect[tuple[ValueT, ...], NewT, TranslatedT, MutatedT, DeadT]:
    effects = tuple(effects)

    if len(effects) == 0:
        return Effect(tuple())

    if len(effects) == 1:
        return effects[0].map(lambda value: (value, ))

    return (
        reduce(Effect.__and__, effects)
        .map(lambda _: tuple(effect.just for effect in effects))
    )


def existing[_ValueT: IdentifiedValue](value: _ValueT) -> Existing[_ValueT]:
    return Effect(value)


def new[_ValueT: IdentifiedValue](value: _ValueT) -> New[_ValueT]:
    return Effect(value, new_values=IdentifiedValueSet([value]))


def translated[ValueT: IdentifiedValue](value: ValueT) -> Translated[ValueT]:
    return Effect(value, translated_values=IdentifiedValueSet([value]))


def mutated[_ValueT: IdentifiedValue](value: _ValueT) -> Mutated[_ValueT]:
    return Effect(value, mutated_values=IdentifiedValueSet([value]))


def dead[ValueT: IdentifiedValue](value: ValueT) -> Dead[ValueT]:
    return Effect(value, dead_values=IdentifiedValueSet([value]))
