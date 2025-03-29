from dataclasses import dataclass

from pytest import fixture, raises

from effect.identity import IdentifiedValue
from effect.state_transition import InvalidStateTransitionError
from effect.sugar import dead, existing, mutated, new, translated


@dataclass(kw_only=True, frozen=True, slots=True)
class X(IdentifiedValue[None]):
    version: int


@fixture
def x_v1() -> X:
    return X(id=None, version=1)


@fixture
def x_v2() -> X:
    return X(id=None, version=1)


def test_new(x_v1: X, x_v2: X) -> None:
    assert new(x_v1) & new(x_v2) == new(x_v2)

    with raises(InvalidStateTransitionError):
        new(x_v1) & translated(x_v2)

    assert new(x_v1) & mutated(x_v2) == new(x_v2)
    assert new(x_v1) & dead(x_v2) == existing(x_v2)
    assert new(x_v1) & existing(x_v2) == new(x_v1)


def test_translated(x_v1: X, x_v2: X) -> None:
    with raises(InvalidStateTransitionError):
        translated(x_v1) & new(x_v2)

    assert translated(x_v1) & translated(x_v2) == translated(x_v2)
    assert translated(x_v1) & mutated(x_v2) == translated(x_v2)
    assert translated(x_v1) & dead(x_v2) == existing(x_v2)
    assert translated(x_v1) & existing(x_v2) == translated(x_v1)


def test_mutated(x_v1: X, x_v2: X) -> None:
    with raises(InvalidStateTransitionError):
        mutated(x_v1) & new(x_v2)

    with raises(InvalidStateTransitionError):
        mutated(x_v1) & translated(x_v2)

    assert mutated(x_v1) & mutated(x_v2) == mutated(x_v2)
    assert mutated(x_v1) & dead(x_v2) == dead(x_v2)
    assert mutated(x_v1) & existing(x_v2) == mutated(x_v1)


def test_dead(x_v1: X, x_v2: X) -> None:
    with raises(InvalidStateTransitionError):
        dead(x_v1) & new(x_v2)

    with raises(InvalidStateTransitionError):
        dead(x_v1) & translated(x_v2)

    with raises(InvalidStateTransitionError):
        dead(x_v1) & mutated(x_v2)

    assert dead(x_v1) & dead(x_v2) == dead(x_v2)
    assert dead(x_v1) & existing(x_v2) == dead(x_v1)
