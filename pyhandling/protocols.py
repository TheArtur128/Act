from typing import runtime_checkable, Protocol, Generic, Any, Optional, Type

from pyhandling.annotations import KeyT, ResultT, ValueT, ContextT


__all__ = (
    "Variable",
)


@runtime_checkable
class Variable(Protocol):
    """
    Protocol describing objects capable of checking another object against a
    subvariant of the describing object (`isinstance(another, describing)`).
    """

    def __instancecheck__(self, instance: object) -> bool:
        ...