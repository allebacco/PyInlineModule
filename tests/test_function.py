import pytest

from pyinlinemodule.function import InlineFunction, METH_NOARGS, METH_O, METH_VARARGS, METH_KEYWORDS

THIS_IS_CPP_CODE = "this_is_cpp_code"


def function_with_cpp_args_kwargs(a, b, c=None, d=3, e=(None, "test")):
    """this is a doctring
    """
    __cpp__ = """
    return Py_BuildValue("(O,O,O,O,O)", a, b, c, d, e);
    """
    return None


def function_with_cpp_args(a, b):
    """this is a doctring
    """
    __cpp__ = """
    return Py_BuildValue("(O,O)", a, b);
    """
    return None


def function_with_cpp_single_args(a):
    """this is a doctring
    """
    __cpp__ = """
    return Py_BuildValue("(O,O)", a, a);
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


def function_with_cpp_code_in_local():
    """this is a doctring
    """
    __cpp__ = "this_is_cpp_code"


def function_with_cpp_code_in_global():
    """this is a doctring
    """
    __cpp__ = THIS_IS_CPP_CODE


@pytest.mark.parametrize('func_call,expected_name', [
    (function_with_cpp_args_kwargs, 'function_with_cpp_args_kwargs'),
    (function_with_cpp_args, 'function_with_cpp_args'),
    (function_with_cpp_single_args, 'function_with_cpp_single_args'),
    (function_with_cpp_noargs, 'function_with_cpp_noargs'),
])
def test_function_name(func_call, expected_name):

    pyfunction = InlineFunction(func_call)
    assert pyfunction.get_name() == expected_name


@pytest.mark.parametrize('func_call,expected_name,meth_def', [
    (function_with_cpp_args_kwargs, 'function_with_cpp_args_kwargs', METH_KEYWORDS),
    (function_with_cpp_args, 'function_with_cpp_args', METH_VARARGS),
    (function_with_cpp_single_args, 'function_with_cpp_single_args', METH_O),
    (function_with_cpp_noargs, 'function_with_cpp_noargs', METH_NOARGS),
])
def test_function_def(func_call, expected_name, meth_def):

    fmt = (expected_name, expected_name, meth_def)
    expected_result = '{"%s",reinterpret_cast<PyCFunction>(%s),%s,nullptr}' % fmt

    pyfunction = InlineFunction(func_call)
    assert pyfunction.get_function_def() == expected_result


@pytest.mark.parametrize('func_call', [
    function_with_cpp_code_in_local, function_with_cpp_code_in_global
])
def test_function_load_cpp_code(func_call):

    pyfunction = InlineFunction(func_call)
    assert pyfunction._cpp_code == THIS_IS_CPP_CODE
