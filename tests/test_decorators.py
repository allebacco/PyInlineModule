import pytest

from pyinlinemodule import Cpp


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



def test_cpp_raise_if_nopython_and_build_error():

    with pytest.raises(RuntimeError):
        @Cpp(no_python=True)
        def compiled_function_no_python_build_error(a):
            __cpp__ = """
            This is a compilation error;
            return PyLong_FromLong(5);
            """
            return a + 7


def test_cpp_does_not_raise_if_build_error_an_use_python():

    @Cpp()
    def compiled_function_no_python_build_error(a):
        __cpp__ = """
        This is a compilation error;
        return PyLong_FromLong(5);
        """
        return a + 7

    assert compiled_function_no_python_build_error(1) == 8
