from typing import Iterable, Callable

from pytest import mark

from pyhandling.tools import to_clone, ArgumentPack, ArgumentKey, DelegatingProperty


class MockObject:
    def __init__(self, **attributes):
        self.__dict__ = attributes

    def __repr__(self) -> str:
        return "<MockObject with {attributes}>".format(
            attributes=str(self.__dict__)[1:-1].replace(': ', '=').replace('\'', '')
        )


def test_to_clone():
    object_ = MockObject(mock_attribute=42)

    cloned_object = to_clone(setattr)(object_, 'mock_attribute', 4)

    assert object_ is not cloned_object
    assert object_.mock_attribute == 42
    assert cloned_object.mock_attribute == 4


@mark.parametrize(
    'args, kwargs',
    [
        ((1, 2, 3), dict(a=4, b=5, c=6)),
        ((1, ), dict(a=4, b=5, c=6)),
        (tuple(), dict(a=4, b=5, c=6)),
        ((1, 2, 3), dict()),
        (tuple(), dict()),
    ]
)
def test_argument_pack_creation_via_call(args: Iterable, kwargs: dict):
    assert ArgumentPack.create_via_call(*args, **kwargs) == ArgumentPack(args, kwargs)


@mark.parametrize(
    'first_args, first_kwargs, second_args, second_kwargs',
    [
        ((1, 2, 3), dict(a=4, b=5, c=6), (4, 5, 6), dict(d=7, e=8, f=9)),
        (tuple(), dict(a=4, b=5, c=6), (4, 5, 6), dict(d=7, e=8, f=9)),
        (tuple(), dict(a=4, b=5, c=6), tuple(), dict(d=7, e=8, f=9)),
        ((1, 2, 3), dict(), (4, 5, 6), dict()),
        (tuple(), dict(), ) * 2,
        ((1, 2, 3), dict(a=4, b=5, c=6), (4, 5, 6), dict(a=7, b=8, c=9)),
    ]
)
def test_argument_pack_merger(
    first_args: Iterable,
    first_kwargs: dict,
    second_args: Iterable,
    second_kwargs: dict
):
    assert (
        ArgumentPack(first_args, first_kwargs).merge_with(ArgumentPack(second_args, second_kwargs))
        == ArgumentPack.create_via_call(*first_args, *second_args, **(first_kwargs | second_kwargs))
    )


@mark.parametrize(
    'first_args, first_kwargs, second_args, second_kwargs',
    [
        ((1, 2, 3), dict(a=4, b=5, c=6), (4, 5, 6), dict(d=7, e=8, f=9)),
        (tuple(), dict(a=4, b=5, c=6), (4, 5, 6), dict(d=7, e=8, f=9)),
        (tuple(), dict(a=4, b=5, c=6), tuple(), dict(d=7, e=8, f=9)),
        ((1, 2, 3), dict(), (4, 5, 6), dict()),
        (tuple(), dict(), ) * 2,
        ((1, 2, 3), dict(a=4, b=5, c=6), (4, 5, 6), dict(a=7, b=8, c=9)),
    ]
)
def test_argument_pack_expanding(
    first_args: Iterable,
    first_kwargs: dict,
    second_args: Iterable,
    second_kwargs: dict
):
    assert (
        ArgumentPack(first_args, first_kwargs).expand_with(*second_args, **second_kwargs)
        == ArgumentPack.create_via_call(*first_args, *second_args, **(first_kwargs | second_kwargs))
    )


@mark.parametrize(
    'func, argument_pack, result',
    [
        (lambda a, b, c: a * b * c, ArgumentPack((1, 2, 3)), 6),
        (lambda a, b, c: a + b + c, ArgumentPack((8, 4), dict(c=30)), 42),
        (lambda a, b, c: a ** b ** c, ArgumentPack(kwargs=dict(a=2, b=2, c=3)), 256),
        (lambda: 48, ArgumentPack(), 48),
    ]
)
def test_argument_pack_calling(func: Callable, argument_pack: ArgumentPack, result: any):
    assert argument_pack.call(func) == result


@mark.parametrize(
    'argument_pack, argument_key, result',
    [
        (ArgumentPack((1, 2, 3)), ArgumentKey(0), 1),
        (ArgumentPack((2, 8, 32, 64, 128), dict(a=1)), ArgumentKey(3), 64),
        (ArgumentPack((4, 2), dict(a=32, b=64, c=128)), ArgumentKey('c', is_keyword=True), 128),
        (ArgumentPack(kwargs=dict(a=1, b=5, c=7)), ArgumentKey('b', is_keyword=True), 5),
    ]
)
def test_argument_pack_getting_argument_by_key(
    argument_pack: ArgumentPack,
    argument_key: ArgumentKey,
    result: any
):
    assert argument_pack[argument_key] == result


@mark.parametrize(
    'delegating_property_kwargs, is_waiting_for_attribute_setting_error',
    [
        (dict(), True),
        (dict(settable=True), False),
        (dict(settable=True), False)
    ]
)
def test_delegating_property_getting(
    delegating_property_kwargs: dict,
    is_waiting_for_attribute_setting_error: bool,
    delegating_property_delegated_attribute_name: str = '_some_attribue'
):
    mock = MockObject(**{delegating_property_delegated_attribute_name: 0})

    property_ = DelegatingProperty(
        delegating_property_delegated_attribute_name,
        **delegating_property_kwargs
    )

    try:
        property_.__set__(mock, 42)
    except AttributeError as error:
        if not is_waiting_for_attribute_setting_error:
            raise error

    assert (
        getattr(mock, delegating_property_delegated_attribute_name)
        == property_.__get__(mock, type(mock))
    )
