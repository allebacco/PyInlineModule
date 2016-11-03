import inspect
import dis
import os
from importlib.machinery import ExtensionFileLoader

from .function import InlineFunction, IFunction
from .inline import build_install_module

# Definition of the C++ class used for the release of the references to the
# Python objects
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
    """Module that can be compiled to a C Extension
    """

    def __init__(self, name):
        """Constructor

        Args:
            name(str): Name of the module.
        """
        self._name = name
        self._functions = list()
        self._cpp_code = ''
        self._cpp_footer = ''

        self._create_footer()

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

        module_init = 'PyMODINIT_FUNC PyInit_%s(void)\n' % self._name
        module_init += '{\n'
        module_init += '    PyObject* module = PyModule_Create(&inline_module);\n'
        module_init += '    if (module == nullptr)\n'
        module_init += '        return nullptr;\n'
        module_init += '    return module;\n'
        module_init += '}\n'

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
        self._cpp_code = ''

    def get_cpp_code(self):
        """C++ code of the module

        Returns:
            str: the C++ code of the module
        """
        if len(self._cpp_code) == 0:
            self._create_code()
        return self._cpp_code

    def _create_code(self):
        """Create the C++ code of the module
        """

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
            function_def += '    {"%s", reinterpret_cast<PyCFunction>(%s), ' % (name, name)
            function_def += 'METH_VARARGS | METH_KEYWORDS, nullptr},\n'
        function_def += '    {NULL, NULL, 0, NULL}\n'
        function_def += '};\n\n'

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
        module_filename = build_install_module(cpp_code, self._name,
                                               module_dir=module_dir, silent=silent)

        if module_filename is None:
            raise ImportError('Module %s could not be load' % self._name)

        # Load module
        file_loader = ExtensionFileLoader(self._name, module_filename)
        imported_module = file_loader.load_module(self._name)
        return imported_module
