import inspect
import dis
import os
from importlib.machinery import ExtensionFileLoader

from .function import InlineFunction, IFunction
from .inline import build_install_module


_OnLeavingScope_class = """

class OnLeavingScope
{
public:
    // Prevent copying
    OnLeavingScope(const OnLeavingScope&) = delete;
    OnLeavingScope& operator=(const OnLeavingScope&) = delete;

    OnLeavingScope(const int count, PyObject*** objects) :
        m_count(count),
        m_objects(objects)
    {}

    ~OnLeavingScope()
    {
        for(int i=0; i<m_count; ++i)
        {
            PyObject** obj = m_objects[i];
            Py_XDECREF(*obj);
        }
    }

private:
    const int m_count;
    PyObject***  m_objects;
};
"""


class InlineModule(object):

    def __init__(self, name):
        self._name = name
        self._functions = list()
        self._cpp_code = ''
        self._cpp_footer = ''

        self._create_footer()

    def _create_footer(self):
        module_def = 'static struct PyModuleDef inline_module = {\n'
        module_def += '    PyModuleDef_HEAD_INIT,\n'
        module_def += '    "%s",\n' % self._name
        module_def += '    nullptr,\n'
        module_def += '    -1,\n'
        module_def += '    module_functions_def\n'
        module_def += '};\n'

        module_init = 'PyMODINIT_FUNC PyInit_%s(void)\n' % self._name
        module_init += '{\n'
        module_init += '    PyObject* module = PyModule_Create(&inline_module);\n'
        module_init += '    if (module == nullptr)\n'
        module_init += '        return nullptr;\n'
        module_init += '    return module;\n'
        module_init += '}\n'

        self._cpp_footer = module_def + '\n\n' + module_init

    def add_function(self, inline_function):
        if not isinstance(inline_function, IFunction):
            inline_function = InlineFunction(inline_function)

        self._functions.append(inline_function)

        # Invalidate CPP code
        self._cpp_code = ''

    def get_cpp_code(self):
        if len(self._cpp_code) == 0:
            self._create_code()
        return self._cpp_code

    def _create_code(self):
        # Build include
        module_header = '''
        #include <Python.h>
        #include <functional>
        #include <pybind11/pybind11.h>

        namespace py = pybind11;

        '''

        module_header += _OnLeavingScope_class + '\n\n'

        # Merge code of all the functions
        function_code = ''
        for function in self._functions:
            function_code += function.get_code()
            function_code += '\n\n'

        # Build method definition
        function_def = 'static PyMethodDef module_functions_def[] = {\n'
        for function in self._functions:
            name = function.get_name()
            function_def += '    {"%s", reinterpret_cast<PyCFunction>(%s), METH_VARARGS | METH_KEYWORDS, nullptr},\n' % (name, name)
        function_def += '    {NULL, NULL, 0, NULL}\n'
        function_def += '};\n\n'

        # Merge all the code in a single source
        cpp_code = module_header + '\n\n'
        cpp_code += function_code + '\n\n'
        cpp_code += function_def + '\n\n'
        cpp_code += self._cpp_footer

        self._cpp_code = cpp_code

    def import_module(self, module_dir=None, silent=True):
        cpp_code = self.get_cpp_code()
        module_filename = build_install_module(cpp_code, self._name,
                                               module_dir=module_dir, silent=silent)

        if module_filename is None:
            raise ImportError('Module %s could not be load' % self._name)

        file_loader = ExtensionFileLoader(self._name, module_filename)
        imported_module = file_loader.load_module(self._name)
        return imported_module
