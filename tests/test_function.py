



def pippo(a, b, c=None, d=3, e=(1, None, "test")):
    """this is a doctring
    """
    __cpp__ = """
    py::tuple args = py::make_tuple(a, b, c, d, e);
    args.inc_ref();
    return args.ptr();
    """

    i = 0
    return 5




def example_run():

    my_module = InlineModule('my_module')
    my_module.add_function(pippo)

    print('Module code')
    #print(my_module.get_cpp_code())

    ext_args = dict()
    if os.name == 'posix':
        ext_args['extra_compile_args'] = ['-O3', '-march=native', '-std=c++11']

    build_install_module('.', my_module.get_cpp_code(), 'my_module', ext_args)