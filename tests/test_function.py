import pytest

from pyinlinemodule.function import InlineFunction


def function_with_cpp_args_kwargs(a, b, c=None, d=3, e=(1, None, "test")):
    """this is a doctring
    """
    __cpp__ = """
    py::tuple args = py::make_tuple(a, b, c, d, e);
    args.inc_ref();
    return args.ptr();
    """
    return None


def function_with_cpp_args(a, b):
    """this is a doctring
    """
    __cpp__ = """
    py::tuple args = py::make_tuple(a, b);
    args.inc_ref();
    return args.ptr();
    """
    return None


def function_with_cpp_noargs():
    """this is a doctring
    """
    __cpp__ = """
    py::tuple args = py::make_tuple(1, 2, 3);
    args.inc_ref();
    return args.ptr();
    """

    i = 0
    return 5


@pytest.mark.parametrize('func_call,expected_name', [
    (function_with_cpp_args_kwargs, 'function_with_cpp_args_kwargs'),
    (function_with_cpp_args, 'function_with_cpp_args'),
    (function_with_cpp_noargs, 'function_with_cpp_noargs'),
])
def test_function_name(func_call, expected_name):

    pyfunction = InlineFunction(func_call)
    assert pyfunction.get_name() == expected_name
