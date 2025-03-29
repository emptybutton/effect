from pytest import fixture, raises

from effect.state_transition import (
    DeadValue,
    InvalidStateTransitionError,
    MutatedValue,
    NewValue,
    NoValue,
    TranslatedValue,
)


@fixture
def x_v1() -> str:
    return "x_v1"


@fixture
def x_v2() -> str:
    return "x_v2"


def test_new(x_v1: str, x_v2: str) -> None:
    assert NewValue(x_v1) & NewValue(x_v2) == NewValue(x_v2)

    with raises(InvalidStateTransitionError):
        NewValue(x_v1) & TranslatedValue(x_v2)

    assert NewValue(x_v1) & MutatedValue(x_v2) == NewValue(x_v2)
    assert NewValue(x_v1) & DeadValue(x_v2) == NoValue(x_v2)
    assert NewValue(x_v1) & NoValue(x_v2) == NewValue(x_v1)


def test_translated(x_v1: str, x_v2: str) -> None:
    with raises(InvalidStateTransitionError):
        TranslatedValue(x_v1) & NewValue(x_v2)

    assert TranslatedValue(x_v1) & TranslatedValue(x_v2) == TranslatedValue(x_v2)
    assert TranslatedValue(x_v1) & MutatedValue(x_v2) == TranslatedValue(x_v2)
    assert TranslatedValue(x_v1) & DeadValue(x_v2) == NoValue(x_v2)
    assert TranslatedValue(x_v1) & NoValue(x_v2) == TranslatedValue(x_v1)


def test_mutated(x_v1: str, x_v2: str) -> None:
    with raises(InvalidStateTransitionError):
        MutatedValue(x_v1) & NewValue(x_v2)

    with raises(InvalidStateTransitionError):
        MutatedValue(x_v1) & TranslatedValue(x_v2)

    assert MutatedValue(x_v1) & MutatedValue(x_v2) == MutatedValue(x_v2)
    assert MutatedValue(x_v1) & DeadValue(x_v2) == DeadValue(x_v2)
    assert MutatedValue(x_v1) & NoValue(x_v2) == MutatedValue(x_v1)


def test_dead(x_v1: str, x_v2: str) -> None:
    with raises(InvalidStateTransitionError):
        DeadValue(x_v1) & NewValue(x_v2)

    with raises(InvalidStateTransitionError):
        DeadValue(x_v1) & TranslatedValue(x_v2)

    with raises(InvalidStateTransitionError):
        DeadValue(x_v1) & MutatedValue(x_v2)

    assert DeadValue(x_v1) & DeadValue(x_v2) == DeadValue(x_v2)
    assert DeadValue(x_v1) & NoValue(x_v2) == DeadValue(x_v1)
