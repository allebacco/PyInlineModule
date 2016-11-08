import warnings

from .module import InlineModule
from .inline import build_install_module


class cpp(object):

    def __init__(self, verbose=False, no_cpp=False, no_python=False, enable_numpy=False, raise_on_error=False):
        self._verbose = verbose
        self._no_cpp = no_cpp
        self._enable_numpy = enable_numpy
        self._no_python = no_python
        self._raise_on_error = raise_on_error

    def __call__(self, func):

        if self._no_cpp:
            return func

        name = func.__module__ + '_' + func.__name__
        try:
            inline_module = InlineModule(name)
            inline_module.add_function(func)
            loaded = inline_module.import_module(silent=False)
            out_function = getattr(loaded, func.__name__)
            print('out_function', out_function)
        except:
            out_function = None
            if self._raise_on_error:
                raise
            elif self._verbose:
                warnings.warn('Unable to inline function %s.%s' % (func.__module__, func.__name__))

        if out_function is None:
            if self._no_python:
                raise RuntimeError('Unable to build C extension for function %s.%s' % (func.__module__, func.__name__))
            else:
                out_function = func

        return out_function



'''
def cpp(func):
    """Decorate a Python function to be compiled to C extension

    Args:
        func(function): The function woth C++ code

    Returns:
        function: The compiled function or the original function if errors happens
            during compilation and function load.
    """
    verbose = True

    name = func.__module__ + '_' + func.__name__
    try:
        inline_module = InlineModule(name)
        inline_module.add_function(func)
        loaded = inline_module.import_module(silent=False)
        return getattr(loaded, func.__name__, func)
    except:
        if verbose:
            import traceback
            traceback.print_exc()
        else:
            warnings.warn('Unable to inline function %s.%s' % (func.__module__, func.__name__))

    return func
'''
