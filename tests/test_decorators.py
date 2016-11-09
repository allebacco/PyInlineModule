import pytest

from pyinlinemodule import cpp


@Cpp()
def compiled_function_cpp(a):
    __cpp__ = """
    long a_value = PyLong_AsLong(a);
    return PyLong_FromLong(a_value + 5);
    """
    return a + 7

@Cpp(no_cpp=True)
def compiled_function_no_cpp(a):
    __cpp__ = """
    long a_value = PyLong_AsLong(a);
    return PyLong_FromLong(a_value + 5);
    """
    return a + 7


@pytest.mark.parametrize('func,arg,expected', [
    (compiled_function_cpp, 3, 3 + 5),
    (compiled_function_no_cpp, 3, 3 + 7)
])
def test_cpp(func, arg, expected):
    assert func(arg) == expected
