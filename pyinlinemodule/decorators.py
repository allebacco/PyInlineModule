import warnings

from .module import InlineModule
from .inline import build_install_module


def cpp(func):
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

