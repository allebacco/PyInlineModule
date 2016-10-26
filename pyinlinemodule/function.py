"""
Copyright (c) 2016 Alessandro Bacchini <allebacco@gmail.com>

All rights reserved. Use of this source code is governed by a
MIT license that can be found in the LICENSE file.
"""

import inspect
import dis
import os


def pippo(a, b, c=None, d=3, e=(1, None, "test")):
    """this is a doctring
    """
    cpp = """
    py::tuple args = py::make_tuple(a, b, c, d, e);
    args.inc_ref();
    return args.ptr();
    """

    i = 0
    return 5


class InlineFunction(object):

    def __init__(self, py_function):
        self._py_function = py_function
        self._signature = inspect.signature(py_function)
        self._cpp_header_code = ''
        self._cpp_code = ''

        self._parse_signature()
        self._build_cpp_code()

    def _parse_signature(self):
        format_string = ''
        default_values = dict()
        is_parsing_kwargs = False
        keyword_args = list()
        variable_names = list()

        for arg in self._signature.parameters.values():
            var_name = arg.name
            keyword_args.append('"%s"' % arg.name)
            variable_names.append(var_name)

            if arg.default is arg.empty:
                format_string += 'O'
            else:
                if not is_parsing_kwargs:
                    format_string += '|'
                is_parsing_kwargs = True
                format_string += 'O'
                default_values[var_name] = repr(arg.default)

        self._build_header_code(variable_names, format_string, keyword_args, default_values)

    def _build_header_code(self, variable_names, format_string, keyword_args, default_values):

        function_name = self._py_function.__name__
        variable_declaration = ('    py::object %s;' % var_name for var_name in variable_names)
        parsing_args = ('&(%s.ptr())' % var_name for var_name in variable_names)

        # Function signature
        function_boilerplate = 'extern "C" PyObject* ' + \
                               function_name + '(PyObject* self, PyObject* args, PyObject* kwargs)\n'
        function_boilerplate += '{\n'

        # Definition of keyword arguments
        function_boilerplate += '    static char* _keywords_[] = {%s};\n' % ','.join(keyword_args)

        # Variable arguments declaration
        function_boilerplate += '\n'.join(variable_declaration)
        function_boilerplate += '\n\n'

        # Arguments parsing
        parsing_args = ', '.join(parsing_args)
        function_boilerplate += '    if(!PyArg_ParseTupleAndKeywords(args, kwargs, "%s", _keywords_, %s))\n' % \
                                (format_string, parsing_args)
        function_boilerplate += '        return nullptr;'
        function_boilerplate += '\n\n'

        # Increment reference counting because py::object decrement it at destruction
        for var_name in variable_names:
            function_boilerplate += '    %s.inc_ref();\n' % var_name
        function_boilerplate += '    \n'

        # Assign default values
        if len(default_values) > 0:
            function_boilerplate += '    PyObject* scope = PyEval_GetGlobals();\n'
            for var_name, default_value in default_values.items():
                function_boilerplate += '    if(%s.ptr() == nullptr)\n' % var_name
                function_boilerplate += '    {\n'
                function_boilerplate += '        static const char* default_value_repr = "%s";\n' % default_value
                function_boilerplate += '        %s.ptr() = PyRun_String(default_value_repr, Py_eval_input, scope, scope);\n' % var_name
                function_boilerplate += '    }\n'

        self._cpp_header_code = function_boilerplate

    def _build_cpp_code(self):
        cpp_code = None

        STORE_FAST = dis.opmap['STORE_FAST']
        LOAD_CONST = dis.opmap['LOAD_CONST']
        for instruction in dis.get_instructions(self._py_function):
            opcode = instruction.opcode
            if opcode == LOAD_CONST:
                cpp_code = instruction.argval
            elif opcode == STORE_FAST and instruction.argval == 'cpp':
                break

        self._cpp_code = cpp_code

    def get_header_code(self):
        return self._cpp_header_code

    def get_name(self):
        return self._py_function.__name__

    def get_code(self):
        return self._cpp_header_code + '\n{\n' + self._cpp_code + '\n}\n}\n'





my_module = InlineModule('my_module')
my_module.add_function(pippo)

print('Module code')
#print(my_module.get_cpp_code())

ext_args = dict()
if os.name == 'posix':
    ext_args['extra_compile_args'] = ['-O3', '-march=native', '-std=c++11']

build_install_module('.', my_module.get_cpp_code(), 'my_module', ext_args)

