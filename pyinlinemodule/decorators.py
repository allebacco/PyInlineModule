import warnings

from .module import InlineModule


class Cpp(object):
    """Decorator for compiling a function with C++ code.

    The function must declare in its code the `__cpp__` variable and assign a static string
    to it with the C++ code that should be executed.
    """

    def __init__(self, verbose=False, no_cpp=False, no_python=False, enable_numpy=False):
        """Constructor of the decorator:

        Keyword Args:
            verbose(bool): Show verbose output of the compilation. Default ``False``.
            no_cpp(bool): Do not compile C code and use Python code. mainly used for debugging and tests.
                Default ``False``.
            no_python(bool): Do not use Python code. If C code can't be compiled, raise an exception.
            enable_numpy(bool): Enable numpy support. Default ``False``.
        """
        self._verbose = verbose
        self._no_cpp = no_cpp
        self._enable_numpy = enable_numpy
        self._no_python = no_python

    def __call__(self, func):
        """Decorate the Python function
        """

        if self._no_cpp:
            return func

        name = func.__module__ + '_' + func.__name__
        try:
            inline_module = InlineModule(name)
            inline_module.add_function(func)
            loaded = inline_module.import_module(silent=False)
            out_function = getattr(loaded, func.__name__)
        except:
            out_function = func
            if self._no_python:
                raise RuntimeError('Unable to build C extension for function %s.%s' % (func.__module__, func.__name__))
            elif self._verbose:
                warnings.warn('Unable to inline function %s.%s' % (func.__module__, func.__name__))

        return out_function
