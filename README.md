# effect
[![CI](https://github.com/emptybutton/effect/actions/workflows/ci.yml/badge.svg)](https://github.com/emptybutton/effect/actions?query=workflow%3ACI)
[![CD](https://github.com/emptybutton/effect/actions/workflows/cd.yaml/badge.svg)](https://github.com/emptybutton/effect/actions/workflows/cd.yaml)
[![GitHub Release](https://img.shields.io/github/v/release/emptybutton/effect?style=flat&logo=github&labelColor=%23282e33&color=%237c73ff)](https://github.com/emptybutton/effect/releases)
[![Lines](https://img.shields.io/endpoint?url=https%3A%2F%2Fghloc.vercel.app%2Fapi%2Femptybutton%2Feffect%2Fbadge%3Ffilter%3D.py&logo=python&label=lines&color=blue)](https://github.com/search?q=repo%3Aemptybutton%2effect+language%3APython+&type=code)

Change tracking library for frozen dataclasses.

## Get
```bash
pip install effectt
```

## Example
```py
from dataclasses import dataclass

from effect import (
    Effect, Identified, LifeCycle, New, existing, just, new, mutated, Existing
)


@dataclass(kw_only=True, frozen=True, slots=True)
class A(Identified[str]):
    id: str
    line: str


@dataclass(kw_only=True, frozen=True, slots=True)
class X(Identified[str]):
    id: str
    a: A | None
    number: int


type SomeX = (
    Existing[X]  # No effects / changes
    | New[X]  # Only `New[X]`
    | Effect[X, A, X]  # `New[A]` and `Mutated[X]`
)


def some_x_when(*, x: X | None, number: int) -> SomeX:
    if x is None:
        return new(X(id="X", a=None, number=number))

    if x.a is not None:
        return existing(x)

    a = new(A(id="A", line=str()))
    x = mutated(X(
        id=x.id,
        number=number,
        a=just(a),
    ))

    return a & x

    # Or without `just`:
    # return a.then(lambda a: mutated(X(
    #     id=x.id,
    #     number=number,
    #     a=a,
    # )))


x = X(id="X", number=4, a=None)

some_x: LifeCycle[X | A]  # All effects / changes for X and A
some_x = some_x_when(x=x, number=8)

assert just(some_x).number == 8
assert some_x.new_values == (A(id='A', line=''),)
assert some_x.mutated_values == (X(id='X', a=A(id='A', line=''), number=4),)
assert some_x.deleted_values == tuple()
```
