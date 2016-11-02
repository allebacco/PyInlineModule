
        #include <Python.h>
        #include <pybind11/pybind11.h>

        namespace py = pybind11;
        

extern "C" PyObject* function_with_cpp_args(PyObject* self, PyObject* args, PyObject* kwargs)
{
    static char* _keywords_[] = {"a","b",nullptr};
    py::object a;
    py::object b;

    if(!PyArg_ParseTupleAndKeywords(args, kwargs, "OO", _keywords_, &(a.ptr()), &(b.ptr())))
        return nullptr;

    a.inc_ref();
    b.inc_ref();
    

    {

    py::tuple args = py::make_tuple(a, b);
    args.inc_ref();
    return args.ptr();
    
    }
}




static PyMethodDef module_functions_def[] = {
    {"function_with_cpp_args", reinterpret_cast<PyCFunction>(function_with_cpp_args), METH_VARARGS | METH_KEYWORDS, nullptr},
    {NULL, NULL, 0, NULL}
};



static struct PyModuleDef inline_module = {
    PyModuleDef_HEAD_INIT,
    "compiled_function_with_cpp_args",
    nullptr,
    -1,
    module_functions_def
};


PyMODINIT_FUNC PyInit_compiled_function_with_cpp_args(void)
{
    PyObject* module = PyModule_Create(&inline_module);
    if (module == nullptr)
        return nullptr;
    return module;
}
