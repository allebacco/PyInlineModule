import inspect
import dis
import os
from importlib.machinery import ExtensionFileLoader
from textwrap import dedent, indent

from .function import InlineFunction, IFunction
from .inline import build_install_module


class InlineModule(object):
    """Module that can be compiled to a C Extension
    """

    def __init__(self, name, enable_numpy=False, enable_pybind11=False):
        """Constructor

        Args:
            name(str): Name of the module.
        """
        self._name = name
        self._functions = list()
        self._cpp_code = ''
        self._cpp_footer = ''
        self._enable_numpy = enable_numpy
        self._enable_pybind11 = enable_pybind11

    def _create_footer(self):
        """Create the module description and initialization function
        """
        module_def = 'static struct PyModuleDef inline_module = {\n'
        module_def += '    PyModuleDef_HEAD_INIT,\n'
        module_def += '    "%s",\n' % self._name
        module_def += '    nullptr,\n'
        module_def += '    -1,\n'
        module_def += '    module_functions_def\n'
        module_def += '};\n'

        other_init_code = ''
        if self._enable_numpy:
            other_init_code += 'import_array();'

        functions_init = '\n'.join((f.get_module_init_code() for f in self._functions))
        module_init = dedent('''
        PyMODINIT_FUNC PyInit_%s(void)
        {
            PyObject* module = PyModule_Create(&inline_module);
            if (module == nullptr)
                return nullptr;

            PyObject* scope = PyEval_GetGlobals();

            %s

            %s

            return module;
        }
        ''') % (self._name, functions_init, other_init_code)

        self._cpp_footer = module_def + '\n\n' + module_init

    def add_function(self, inline_function):
        """Add a function to the module

        Args:
            inline_function(function,InlineFunction): A function that can be compiled in a C extension
        """
        if not isinstance(inline_function, IFunction):
            inline_function = InlineFunction(inline_function)

        self._functions.append(inline_function)

        # Invalidate CPP code
        self._reset()

    def set_enable_numpy(self, enable=True):
        """Enable the support for `numpy` C API

        Keyword Args:
            enable(bool): ``True`` for enabling `numpy` support, ``False`` to disable it.
        """
        self._enable_numpy = enable
        self._reset()

    def get_cpp_code(self):
        """C++ code of the module

        Returns:
            str: the C++ code of the module
        """
        if len(self._cpp_code) == 0:
            self._create_code()
        return self._cpp_code

    def _reset(self):
        self._cpp_code = ''
        self._cpp_footer = ''

    def _create_code(self):
        """Create the C++ code of the module
        """

        self._create_footer()

        # Build include
        module_header = dedent('''
        #include <Python.h>

        ''')

        if self._enable_numpy:
            module_header += dedent('''
            #define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
            #define PY_ARRAY_UNIQUE_SYMBOL  numpy_ARRAY_API
            #include <numpy/arrayobject.h>
            ''')

        for function in self._functions:
            module_header += function.get_module_header_code() + '\n\n'

        # Merge code of all the functions
        function_code = ''
        for function in self._functions:
            function_code += function.get_code()
            function_code += '\n\n'

        # Build method definition

        function_def_iter = (f.get_function_def() for f in self._functions)
        function_def = dedent('''
        static PyMethodDef module_functions_def[] = {
            %s,
            nullptr
        };
        ''') % '    ,\n'.join(function_def_iter)

        # Merge all the code in a single source
        cpp_code = module_header + '\n\n'
        cpp_code += function_code + '\n\n'
        cpp_code += function_def + '\n\n'
        cpp_code += self._cpp_footer

        self._cpp_code = cpp_code

    def import_module(self, module_dir=None, silent=True):
        """Build an import the module

        Keyword Args:
            module_dir(str): The location to store all the files of the module (source, temporary objects,
                shared object). Default to a temporary location.
            silent(bool): Silent compilation. Default True

        Returns:
            The loaded C extension

        Raises:
            ImportError: if the C++ code could not be compiled or the module could not be loaded
        """
        # Build module
        cpp_code = self.get_cpp_code()

        extension_kwargs = dict()
        if self._enable_numpy:
            import numpy as np
            extension_kwargs['include_dirs'] = [np.get_include()]

        module_filename = build_install_module(cpp_code, self._name, extension_kwargs=extension_kwargs,
                                               module_dir=module_dir, silent=silent)

        if module_filename is None:
            raise ImportError('Module %s could not be load' % self._name)

        # Load module
        file_loader = ExtensionFileLoader(self._name, module_filename)
        imported_module = file_loader.load_module(self._name)
        return imported_module
