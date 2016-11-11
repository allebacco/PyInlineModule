"""
Copyright (c) 2016 Alessandro Bacchini <allebacco@gmail.com>

All rights reserved. Use of this source code is governed by a
MIT license that can be found in the LICENSE file.
"""

import inspect
import dis
import os
from textwrap import dedent, indent


STORE_FAST = dis.opmap['STORE_FAST']
LOAD_CONST = dis.opmap['LOAD_CONST']

METH_NOARGS = 'METH_NOARGS'
METH_O = 'METH_O'
METH_VARARGS = 'METH_VARARGS'
METH_KEYWORDS = 'METH_VARARGS | METH_KEYWORDS'


class IFunction(object):
    """Base interface of a function that can be compiled in an C extension
    """

    def get_name(self):
        """Name of the function

        Returns:
            str: The name of the function
        """
        raise NotImplementedError()

    def get_code(self):
        """C++ code of the function

        Returns:
            str: The C++ code of the function
        """
        raise NotImplementedError()

    def get_function_def(self):
        """`PyMethodDef` of the function

        The returned string should be in format::

            {"name of the method", <name of the C function>, <call flags>, <doc or nullptr>}

        No trailing comma should be appended.

        Returns:
            str: The `PyMethodDef` description of the function
        """
        raise NotImplementedError()

    def get_module_init_code(self):
        """C++ code that should be executed in the module init function

        Returns:
            str: The C++ code to execute during module init
        """
        return ''

    def get_module_header_code(self):
        """C++ code to be placed before the all the function code

        Returns:
            str: The C++ code to place before functions
        """
        return ''


class InlineFunction(IFunction):
    """Function that can be compiled in an C extension.

    A function can be compiled to C extension if contains the C++ code that shoud
    be executed:

    ::

       def a_compilable_function(arg1, arg2, arg3=10):
           '''The docstring
           '''
           a = 4
           b = call_to_a_function(1)
           __cpp__ = '''
           // The C++ code that should be compiled and executed
           Py_RETURN_NONE;
           '''
           return a + b

    The C++ code can assume that the argument of the function exists even within the C++ code.
    """

    def __init__(self, py_function):
        """Constructor

        Args:
            py_function(function): The Python function with C++ code
        """
        super().__init__()
        self._py_function = py_function
        self._signature = inspect.signature(py_function)
        self._cpp_header_code = ''
        self._cpp_code = ''
        self._function_def = ''
        self._module_init_code = ''
        self._module_header_code = ''

        self._parse_signature()
        self._create_cpp()

    def _parse_signature(self):
        """Parse the signature of the function
        """
        format_string = ''
        default_values = dict()
        is_parsing_kwargs = False
        variable_names = list()

        for arg in self._signature.parameters.values():
            var_name = arg.name
            variable_names.append(var_name)

            if arg.default is arg.empty:
                format_string += 'O'
            else:
                if not is_parsing_kwargs:
                    format_string += '|'
                is_parsing_kwargs = True
                format_string += 'O'
                default_values[var_name] = repr(arg.default)

        self._create_header(variable_names, format_string, default_values)

    def _create_header(self, variable_names, format_string, default_values):
        """Create the signature and argument parsing code of the C++ function
        """
        num_variable = len(variable_names)
        num_keyword_args = len(default_values)

        if num_variable == 0:
            self._create_header_noargs()
        elif num_variable == 1 and num_keyword_args == 0:
            self._create_header_single_arg(variable_names[0])
        elif num_variable > 1 and num_keyword_args == 0:
            self._create_header_varargs(variable_names, format_string)
        else:
            self._create_header_keywords(variable_names, format_string, default_values)

    def _create_header_noargs(self):
        function_name = self._py_function.__name__

        # Function signature
        function_boilerplate = 'extern "C" PyObject* {0}(PyObject* self)\n'.format(function_name)
        function_boilerplate += '{\n'

        self._cpp_header_code = function_boilerplate

        function_def = [
            '"%s"' % function_name,
            'reinterpret_cast<PyCFunction>(%s)' % function_name,
            METH_NOARGS,
            "nullptr"
        ]

        self._function_def = '{' + ','.join(function_def) + '}'

    def _create_header_single_arg(self, variable_name):
        function_name = self._py_function.__name__

        # Function signature
        function_boilerplate = 'extern "C" ' \
            'PyObject* {0}(PyObject* self, PyObject* {1})\n'.format(function_name, variable_name)
        function_boilerplate += '{\n'

        self._cpp_header_code = function_boilerplate

        function_def = [
            '"%s"' % function_name,
            'reinterpret_cast<PyCFunction>(%s)' % function_name,
            METH_O,
            "nullptr"
        ]

        self._function_def = '{' + ','.join(function_def) + '}'

    def _create_header_varargs(self, variable_names, format_string):
        function_name = self._py_function.__name__

        # Function signature
        function_boilerplate = 'extern "C" PyObject* {0}(PyObject* self, PyObject* args)\n'.format(function_name)
        function_boilerplate += '{\n'

        # Variable arguments declaration
        variable_declaration = ('PyObject* %s = nullptr;' % var_name for var_name in variable_names)
        function_boilerplate += indent('\n'.join(variable_declaration), '    ')
        function_boilerplate += '\n\n'

        # Arguments parsing
        parsing_args = ('&' + var_name for var_name in variable_names)
        parsing_args = ', '.join(parsing_args)
        parsetuple = dedent('''
        if(!PyArg_ParseTuple(args, "{0}", {1}))
            return nullptr;
        ''').format(format_string, parsing_args)
        function_boilerplate += indent(parsetuple, '    ')
        function_boilerplate += '\n'

        self._cpp_header_code = function_boilerplate

        function_def = [
            '"%s"' % function_name,
            'reinterpret_cast<PyCFunction>(%s)' % function_name,
            METH_VARARGS,
            "nullptr"
        ]

        self._function_def = '{' + ','.join(function_def) + '}'

    def _create_header_keywords(self, variable_names, format_string, default_values):
        function_name = self._py_function.__name__

        # Function signature
        keyword_names = ('"%s"' % arg for arg in variable_names)
        func_signature = dedent('''
        extern "C" PyObject* %s(PyObject* self, PyObject* args, PyObject* kwargs)
        {
            static char* _keywords_[] = {%s,nullptr};
        ''') % (function_name, ','.join(keyword_names))

        function_boilerplate = func_signature

        # Variable arguments declaration
        for var_name in variable_names:
            if var_name in default_values.keys():
                dec = 'PyObject* {0} = __{1}_{0};\n'.format(var_name, function_name)
            else:
                dec = 'PyObject* {0} = nullptr;\n'.format(var_name)
            function_boilerplate += indent(dec, '    ')

        function_boilerplate += '\n'

        # Arguments parsing
        parsing_args = ('&' + var_name for var_name in variable_names)
        parsing_args = ', '.join(parsing_args)
        parsetuplekewords = dedent('''
        if(!PyArg_ParseTupleAndKeywords(args, kwargs, "{0}", _keywords_, {1}))
            return nullptr;
        ''').format(format_string, parsing_args)
        function_boilerplate += indent(parsetuplekewords, '    ')
        function_boilerplate += '\n'

        self._cpp_header_code = function_boilerplate

        kwargs_header_def = (
            'static PyObject* __{0}_{1} = nullptr;'.format(function_name, arg)
            for arg in default_values.keys()
        )
        self._module_header_code = '\n'.join(kwargs_header_def)

        # Add default values of keyword arguments to static PyObject variables
        # and registeer them as module objects to move the responsibility of
        # their reference counting to Python module itself
        module_init = '{\n'
        for var_name, default_value in default_values.items():
            kwarg_init_default = dedent('''
            static const char* default_value_repr = "{0}";
            __{1}_{2} = PyRun_String(default_value_repr, Py_eval_input, scope, scope);
            PyModule_AddObject(module, "__{1}_{2}", __{1}_{2});
            ''').format(default_value, function_name, var_name)
            module_init += '{\n%s\n}\n' % indent(kwarg_init_default, '    ')
        module_init += '}\n'

        self._module_init_code = indent(module_init, '    ')

        function_def = [
            '"%s"' % function_name,
            'reinterpret_cast<PyCFunction>(%s)' % function_name,
            METH_KEYWORDS,
            "nullptr"
        ]
        self._function_def = '{' + ','.join(function_def) + '}'

    def _create_cpp(self):
        """Extract the C++ code from the function
        """
        cpp_code = None

        for instruction in dis.get_instructions(self._py_function):
            opcode = instruction.opcode
            if opcode == LOAD_CONST:
                cpp_code = instruction.argval
            elif opcode == STORE_FAST and instruction.argval == '__cpp__':
                break

        self._cpp_code = cpp_code

    def get_name(self):
        return self._py_function.__name__

    def get_code(self):
        return self._cpp_header_code + '\n    {\n' + self._cpp_code + '\n    }\n}\n'

    def get_function_def(self):
        return self._function_def

    def get_module_init_code(self):
        return self._module_init_code

    def get_module_header_code(self):
        return self._module_header_code
