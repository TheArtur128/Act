from collections import OrderedDict
from functools import cached_property, partial
from dataclasses import dataclass, field
from inspect import Signature
from types import MappingProxyType
from typing import (
    Final, Generic, Iterable, Optional, Tuple, Self, Any, Callable, TypeVar,
)

from pyannotating import Special

from pyhandling.annotations import KeyT, ValueT
from pyhandling.atoming import atomically
from pyhandling.signature_assignmenting import (
    Decorator, call_signature_of
)


__all__ = ("ArgumentKey", "Arguments", "as_arguments", "unpackly")


_EMPTY_DEFAULT_VALUE: Final[object] = object()

_ArgumentKeyT = TypeVar("_ArgumentKeyT", bound=int | str)


@dataclass(frozen=True, repr=False)
class ArgumentKey(Generic[_ArgumentKeyT, ValueT]):
    """
    Data class for structuring getting value from `Arguments` via `[]`.
    """

    value: _ArgumentKeyT
    is_keyword: bool = field(default=False, kw_only=True)
    default: ValueT = field(
        default_factory=lambda: _EMPTY_DEFAULT_VALUE,
        compare=False,
        kw_only=True,
    )

    def __post_init__(self) -> None:
        if (
            isinstance(self.value, int) and self.is_keyword
            or isinstance(self.value, str) and not self.is_keyword
        ):
            raise ArgumentError("keyword ArgumentKey value must be a string")

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self)})"

    def __str__(self, *, with_position: bool = True) -> str:
        formatted_key = (
            str(self.value) if with_position or self.is_keyword else '...'
        )

        formatted_value = (
            '...' if self.default is _EMPTY_DEFAULT_VALUE else str(self.default)
        )

        return (
            f"{formatted_key}={formatted_value}"
            if self.is_keyword
            else formatted_key
        )
class Arguments(Mapping, Generic[ValueT]):
    """
    Data class for structuring the storage of any arguments.

    Has the ability to get an attribute when passed to `[]` `ArgumentKey`
    instance.
    """

    def __init__(
        self,
        args: Iterable = tuple(),
        kwargs: Optional[dict] = None,
    ):
        self._args = tuple(args)
        self._kwargs = MappingProxyType(
            kwargs if kwargs is not None else dict()
        )

    @property
    def args(self) -> Tuple:
        return self._args

    @property
    def kwargs(self) -> MappingProxyType:
        return self._kwargs

    @cached_property
    def keys(self) -> Tuple[ArgumentKey, ...]:
        return (
            *map(ArgumentKey, range(len(self.args))),
            *map(partial(ArgumentKey, is_keyword=True), self.kwargs.keys())
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__str__()})"

    def __str__(self) -> str:
        return "{formatted_args}{argument_separation_part}{formatted_kwargs}".format(
            formatted_args=', '.join(map(str, self.args)),
            argument_separation_part=(
                ', ' if self.args and self.kwargs else str(),
            ),
            formatted_kwargs=', '.join(map(
                lambda item: f"{item[0]}={item[1]}",
                self.kwargs.items())
            ),
        )


    def __eq__(self, other: Special[Self]) -> bool:
        return (
            isinstance(other, Arguments)
            and self.args == other.args
            and self.kwargs == other.kwargs
        )

    def __getitem__(self, argument: ArgumentKey) -> Any:
        return (
            (self.kwargs if argument.is_keyword else self.args)[argument.key]
            if argument in self or argument.default is _EMPTY_DEFAULT_VALUE
            else argument.default
        )

    def __or__(self, other: Self) -> Self:
        return self.merge_with(other)

    def __contains__(self, argument: ArgumentKey) -> bool:
        return argument in self.keys

    def expand_with(self, *args, **kwargs) -> Self:
        """Method to create another pack with input arguments."""

        return self.__class__(
            (*self.args, *args),
            self.kwargs | kwargs
        )

    def merge_with(self, argument_pack: Self) -> Self:
        """
        Method to create another pack by merging with an input argument pack.
        """

        return self.__class__(
            (*self.args, *argument_pack.args),
            self.kwargs | argument_pack.kwargs
        )

    def only_with(self, *argument_keys: ArgumentKey) -> Self:
        """Method for cloning with values obtained from input keys."""

        keyword_argument_keys = set(filter(
            lambda argument_key: argument_key.is_keyword,
            argument_keys
        ))

        return self.__class__(
            tuple(
                self[argument_key]
                for argument_key in set(argument_keys) - keyword_argument_keys
            ),
            {
                keyword_argument_key.key: self[keyword_argument_key]
                for keyword_argument_key in keyword_argument_keys
            },
        )

    def without(self, *argument_keys: ArgumentKey) -> Self:
        """
        Method for cloning a pack excluding arguments whose keys are input to
        this method.
        """

        return self.only_with(*OrderedDict.fromkeys((
            *self.keys,
            *argument_keys,
        )))

    def call(self, caller: Callable) -> Any:
        """
        Method for calling an input function with arguments stored in an
        instance.
        """

        return caller(*self.args, **self.kwargs)

    @classmethod
    def of(cls, *args, **kwargs) -> Self:
        """Method for creating a pack with this method's input arguments."""

        return cls(args, kwargs)



def as_arguments(*args, **kwargs) -> Arguments:
    """
    Function to optionally convert input arguments into `Arguments`.
    When passed a single positional `Arguments` to the function, it returns it.
    """

    if len(args) == 1 and isinstance(args[0], Arguments) and not kwargs:
        return args[0]

    return Arguments(args, kwargs)


@atomically
class unpackly(Decorator):
    """Decorator to unpack the input `Arguments` into an input action."""

    def __call__(self, arguments: Arguments) -> Any:
        return arguments.call(self._action)

    @cached_property
    def _force_signature(self) -> Signature:
        return call_signature_of(self).replace(return_annotation=(
            call_signature_of(self._action).return_annotation
        ))
