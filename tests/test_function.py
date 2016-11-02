import pytest

from pyinlinemodule.function import InlineFunction


def function_with_cpp_args_kwargs(a, b, c=None, d=3, e=(None, "test")):
    """this is a doctring
    """
    __cpp__ = """
    return PyBuildValue("(O,O,O,O,O)", a, b, c, d, e);
    """
    return None


def function_with_cpp_args(a, b):
    """this is a doctring
    """
    __cpp__ = """
    return PyBuildValue("(O,O)", a, b);
    """
    return None


def function_with_cpp_noargs():
    """this is a doctring
    """
    __cpp__ = """
    return Py_BuildValue("(i,i,i)", 1, 2, 3);
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
