"""
Copyright (c) 2016 Alessandro Bacchini <allebacco@gmail.com>

All rights reserved. Use of this source code is governed by a
MIT license that can be found in the LICENSE file.
"""

import inspect
import dis
import os


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
        function_boilerplate = 'extern "C" PyObject* ' + function_name + '(PyObject* self)\n'
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
        function_boilerplate = 'extern "C" PyObject* ' + function_name
        function_boilerplate += '(PyObject* self, PyObject* %s)\n' % variable_name
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
        function_boilerplate = 'extern "C" PyObject* ' + \
                               function_name + '(PyObject* self, PyObject* args)\n'
        function_boilerplate += '{\n'

        # Variable arguments declaration
        variable_declaration = ('    PyObject* %s = nullptr;' % var_name for var_name in variable_names)
        function_boilerplate += '\n'.join(variable_declaration)
        function_boilerplate += '\n\n'

        # Arguments parsing
        parsing_args = ('&%s' % var_name for var_name in variable_names)
        parsing_args = ', '.join(parsing_args)
        function_boilerplate += '    if(!PyArg_ParseTuple(args, "%s", %s))\n' % \
                                (format_string, parsing_args)
        function_boilerplate += '        return nullptr;'
        function_boilerplate += '\n\n'

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
        function_boilerplate = 'extern "C" PyObject* ' + \
                               function_name + '(PyObject* self, PyObject* args, PyObject* kwargs)\n'
        function_boilerplate += '{\n'

        # Definition of keyword arguments
        keyword_names = ('"%s"' % arg for arg in variable_names)
        function_boilerplate += '    static char* _keywords_[] = {%s,nullptr};\n' % ','.join(keyword_names)

        # Variable arguments declaration
        variable_declaration = ('    PyObject* %s = nullptr;' % var_name for var_name in variable_names)
        function_boilerplate += '\n'.join(variable_declaration)
        function_boilerplate += '\n\n'

        dec_ref_variables = ('&%s' % var_name for var_name in variable_names)
        function_boilerplate += '    PyObject** __obj_to_be_released[] = {%s};' % ','.join(dec_ref_variables)
        function_boilerplate += '    OnLeavingScope __on_leaving_scope('
        function_boilerplate += '%d, __obj_to_be_released);\n\n' % len(variable_names)

        # Arguments parsing
        parsing_args = ('&%s' % var_name for var_name in variable_names)
        parsing_args = ', '.join(parsing_args)
        function_boilerplate += '    if(!PyArg_ParseTupleAndKeywords(args, kwargs, "%s", _keywords_, %s))\n' % \
                                (format_string, parsing_args)
        function_boilerplate += '        return nullptr;'
        function_boilerplate += '\n\n'

        # Increment reference counting because OnLeavingScope instance decrements them at destruction
        for var_name in variable_names:
            function_boilerplate += '    Py_XINCREF(%s);\n' % var_name
        function_boilerplate += '    \n'

        # Assign default values
        if len(default_values) > 0:
            function_boilerplate += '    PyObject* scope = PyEval_GetGlobals();\n'
            for var_name, default_value in default_values.items():
                function_boilerplate += '    if(%s == nullptr)\n' % var_name
                function_boilerplate += '    {\n'
                function_boilerplate += '        static const char* default_value_repr = "%s";\n' % default_value
                function_boilerplate += '        %s = PyRun_String(default_value_repr, Py_eval_input, scope, scope);\n' % var_name
                function_boilerplate += '    }\n'

        self._cpp_header_code = function_boilerplate

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
