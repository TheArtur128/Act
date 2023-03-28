from abc import ABC, abstractmethod
from functools import cached_property
from types import MappingProxyType
from typing import Generic, Union, runtime_checkable, Protocol, Iterable, Self, Tuple, NamedTuple, Optional, ClassVar

from pyannotating import Special, AnnotationTemplate, input_annotation

from pyhandling.annotations import ErrorT, ContextT
from pyhandling.errors import PyhandingError
from pyhandling.language import to
from pyhandling.tools import DelegatingProperty, with_opened_items
from pyhandling.utils import ContextRoot


__all__ = (
    "MechanicalError", "SingleErrorKepper", "ErrorKepper", "error_storage_of",
    "errors_from", "ContextualError", "error_root_from"
)


class MechanicalError(PyhandingError):
    pass


@runtime_checkable
class SingleErrorKepper(Protocol, Generic[ErrorT]):
    error: ErrorT | Self | "ErrorKepper"


@runtime_checkable
class ErrorKepper(Protocol, Generic[ErrorT]):
    errors: Iterable[Self | SingleErrorKepper[ErrorT] | ErrorT]


error_storage_of = AnnotationTemplate(Union, [
    AnnotationTemplate(ErrorKepper, [input_annotation]),
    AnnotationTemplate(SingleErrorKepper, [input_annotation])
])


def errors_from(error_storage: error_storage_of[ErrorT] | ErrorT) -> Tuple[ErrorT]:
    """
    Function to recursively get all (including nested) errors from unstructured
    error storage.
    """

    errors = (error_storage, ) if isinstance(error_storage, Exception) else tuple()

    if isinstance(error_storage, SingleErrorKepper):
        errors += errors_from(error_storage.error)
    if isinstance(error_storage, ErrorKepper):
        errors += with_opened_items(map(errors_from, error_storage.errors))

    return errors


class ContextualError(MechanicalError, Generic[ErrorT, ContextT]):
    """Error class to store the context of another error and itself."""
   
    error = DelegatingProperty("_ContextualError__error")
    context = DelegatingProperty("_ContextualError__context")

    def __init__(self, error: ErrorT, context: ContextT):
        self.__error = error
        self.__context = context

        super().__init__(self._error_message)

    @cached_property
    def _error_message(self) -> str:
        return f"{str(self.__error)} when {self.__context}"


def error_root_from(
    error: ContextualError[ErrorT, ContextT]
) -> ContextRoot[ErrorT, ContextT]:
    """Converter function from `ContextualError` to `ContextRoot`."""

    return ContextRoot(error.error, error.context)