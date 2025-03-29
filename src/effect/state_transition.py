from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True, slots=True, repr=False)
class ValueWithState[JustT = Any](ABC):
    just: JustT
    state_name: ClassVar[str]

    def __repr__(self) -> str:
        return f"{self.state_name}({self.just})"

    @abstractmethod
    def __and__[NextJustT](
        self, next_value: "TransitionOperand[NextJustT]"
    ) -> "TransitionOperand[JustT | NextJustT]": ...


type TransitionOperand[T] = (
    NewValue
    | TranslatedValue
    | MutatedValue
    | DeadValue
    | NoValue
)


class InvalidStateTransitionError(Exception):
    def __init__(self, was: ValueWithState, became: ValueWithState) -> None:
        super().__init__(
            f"{was} -> {became}"
        )


class NoValue[JustT = Any](ValueWithState[JustT]):
    state_name = "no"

    def __and__[NextJustT](
        self, next_value: "TransitionOperand[NextJustT]"
    ) -> "TransitionOperand[JustT | NextJustT]":
        return next_value


class NewValue[JustT = Any](ValueWithState[JustT]):
    state_name = "new"

    def __and__[NextJustT](
        self, next_value: "TransitionOperand[NextJustT]"
    ) -> "TransitionOperand[JustT | NextJustT]":
        match next_value:
            case NewValue():
                return next_value
            case TranslatedValue():
                raise InvalidStateTransitionError(was=self, became=next_value)
            case MutatedValue(just):
                return NewValue(just)
            case DeadValue(just):
                return NoValue(just)
            case NoValue():
                return self


class TranslatedValue[JustT = Any](ValueWithState[JustT]):
    state_name = "translated"

    def __and__[NextJustT](
        self, next_value: "TransitionOperand[NextJustT]"
    ) -> "TransitionOperand[JustT | NextJustT]":
        match next_value:
            case NewValue():
                raise InvalidStateTransitionError(was=self, became=next_value)
            case TranslatedValue():
                return next_value
            case MutatedValue(just):
                return TranslatedValue(just)
            case DeadValue(just):
                return NoValue(just)
            case NoValue():
                return self


class MutatedValue[JustT = Any](ValueWithState[JustT]):
    state_name = "mutated"

    def __and__[NextJustT](
        self, next_value: "TransitionOperand[NextJustT]"
    ) -> "TransitionOperand[JustT | NextJustT]":
        match next_value:
            case NewValue():
                raise InvalidStateTransitionError(was=self, became=next_value)
            case TranslatedValue():
                raise InvalidStateTransitionError(was=self, became=next_value)
            case MutatedValue():
                return next_value
            case DeadValue():
                return next_value
            case NoValue():
                return self


class DeadValue[JustT = Any](ValueWithState[JustT]):
    state_name = "dead"

    def __and__[NextJustT](
        self, next_value: "TransitionOperand[NextJustT]"
    ) -> "TransitionOperand[JustT | NextJustT]":
        match next_value:
            case NewValue():
                raise InvalidStateTransitionError(was=self, became=next_value)
            case TranslatedValue():
                raise InvalidStateTransitionError(was=self, became=next_value)
            case MutatedValue():
                raise InvalidStateTransitionError(was=self, became=next_value)
            case DeadValue():
                return next_value
            case NoValue():
                return self
