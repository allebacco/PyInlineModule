import sys
import pytest
import numpy as np

from pyinlinemodule.module import InlineModule


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


def function_with_cpp_single_arg(a):
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


def function_with_cpp_numpy_returns_arange(start, stop, step):
    """this is a doctring
    """
    __cpp__ = """
    return PyArray_Arange(PyFloat_AsDouble(start), PyFloat_AsDouble(stop), PyFloat_AsDouble(step), NPY_FLOAT64);
    """

    i = 0
    return 5


@pytest.fixture(scope='module')
def compiled_function_with_cpp_args_kwargs():
    inline_module = InlineModule('compiled_function_with_cpp_args_kwargs')
    inline_module.add_function(function_with_cpp_args_kwargs)
    return inline_module.import_module(), 'function_with_cpp_args_kwargs'


@pytest.fixture(scope='module')
def compiled_function_with_cpp_args():
    inline_module = InlineModule('compiled_function_with_cpp_args')
    inline_module.add_function(function_with_cpp_args)
    return inline_module.import_module(), 'function_with_cpp_args'


@pytest.fixture(scope='module')
def compiled_function_with_cpp_single_arg():
    inline_module = InlineModule('compiled_function_with_cpp_single_arg')
    inline_module.add_function(function_with_cpp_single_arg)
    return inline_module.import_module(), 'function_with_cpp_single_arg'


@pytest.fixture(scope='module')
def compiled_function_with_cpp_noargs():
    inline_module = InlineModule('compiled_function_with_cpp_noargs')
    inline_module.add_function(function_with_cpp_noargs)
    return inline_module.import_module(), 'function_with_cpp_noargs'


@pytest.mark.parametrize('return_value', [(1, 2, 3)])
def test_compile_single_function_noargs(compiled_function_with_cpp_noargs, return_value):

    tested_module, func_name = compiled_function_with_cpp_noargs

    assert hasattr(tested_module, func_name)

    compiled_function = getattr(tested_module, func_name)
    result = compiled_function()
    assert result == return_value

    # ensuring only one reference existx, plus the reference in the sys.getrefcount() function
    assert sys.getrefcount(result) == 2


@pytest.mark.parametrize('args,kwargs,return_value', [
    ((1, 2), dict(), (1, 2, None, 3, (None, "test"))),
    ((1, 2), dict(e=5), (1, 2, None, 3, 5)),
    ((1, 2, 7), dict(), (1, 2, 7, 3, (None, "test"))),
    ((1, 2, 'str'), dict(e=None), (1, 2, 'str', 3, None)),
])
def test_compile_single_function_with_kwargs(compiled_function_with_cpp_args_kwargs, args, kwargs, return_value):

    tested_module, func_name = compiled_function_with_cpp_args_kwargs

    assert hasattr(tested_module, func_name)

    compiled_function = getattr(tested_module, func_name)

    result = compiled_function(*args, **kwargs)
    assert result == return_value

    # ensuring only one reference exists, plus the reference in the sys.getrefcount() function
    assert sys.getrefcount(result) == 2


@pytest.mark.parametrize('args,return_value', [
    ((1, 2), (1, 2)),
    ((1, []), (1, [])),
])
def test_compile_single_function_with_args(compiled_function_with_cpp_args, args, return_value):

    tested_module, func_name = compiled_function_with_cpp_args

    assert hasattr(tested_module, func_name)

    compiled_function = getattr(tested_module, func_name)

    result = compiled_function(*args)
    assert result == return_value

    # ensuring only one reference exists, plus the reference in the sys.getrefcount() function
    assert sys.getrefcount(result) == 2


@pytest.mark.parametrize('arg,return_value', [(1, (1, 1)), ([1], ([1], [1]))])
def test_compile_single_function_with_single_args(compiled_function_with_cpp_single_arg, arg, return_value):

    tested_module, func_name = compiled_function_with_cpp_single_arg

    assert hasattr(tested_module, func_name)

    compiled_function = getattr(tested_module, func_name)

    result = compiled_function(arg)
    assert result == return_value

    # ensuring only one reference exists, plus the reference in the sys.getrefcount() function
    assert sys.getrefcount(result) == 2


@pytest.mark.parametrize('py_function,function_name,args,return_value', [
    (
        function_with_cpp_numpy_returns_arange,
        'function_with_cpp_numpy_returns_arange',
        (0., 10., 1.),
        np.arange(0., 10., 1., dtype=np.float64)
    ),
])
def test_compile_single_function_with_numpy(py_function, function_name, args, return_value):

    inline_module = InlineModule('test_compile_single_function_with_numpy', enable_numpy=True)
    inline_module.add_function(py_function)
    tested_module = inline_module.import_module()

    assert hasattr(tested_module, function_name)

    compiled_function = getattr(tested_module, function_name)

    result = compiled_function(*args)
    assert np.all(result == return_value)

