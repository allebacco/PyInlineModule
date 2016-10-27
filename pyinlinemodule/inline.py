import os
import tempfile
import atexit
import shutil


_PATH = tempfile.mkdtemp(prefix='pyinline_tmp_')
_EXTRA_COMPILE_ARGS = []
_MOD_EXTENSION = 'pyd'


# Remove the temporary directory at exit
atexit.register(shutil.rmtree, _PATH)

if os.name == 'posix':
    # Compile args for Linux systems, in particular GCC
    _EXTRA_COMPILE_ARGS += ['-O3', '-march=native', '-std=c++11']
    _MOD_EXTENSION = 'so'


def extra_compile_args():
    return _EXTRA_COMPILE_ARGS[::]


def build_install_module(module_src, mod_name, extension_kwargs, mod_dir=None, silent=True):
    """Build and install the compiled C Extension in the provided (or default) folder.

    Args:
        module_src(str): C++ source code of the module.
        mod_name(str): Name of the module.
        extension_kwargs(dict): Extra arguments for the compilation of the extension module.

    Keyword Args:
        mod_dir(str): Folder in which the module must be biult and installed. Default
            to a temporary folder.
        silent(bool): Disable verbosity logging. Default ``True``

    Returns:
        str,None: The filename of the compiled module or ``None`` if errors happens
            during compilation
    """

    # Save the current path so we can reset at the end of this function.
    curpath = os.getcwd()
    mod_name_c = mod_name + '.cpp'

    if mod_dir is None:
        mod_dir = str(_PATH)

    # Change to the code directory.
    os.chdir(mod_dir)

    module_filename = None
    try:
        from distutils.core import setup, Extension
        import pybind11

        with open(mod_name_c, 'w') as module_cpp_file:
            # Write out the code.
            module_cpp_file.write(module_src)

        # Ensure the original extension_kwargs will not be modified
        extension_kwargs = extension_kwargs.copy()

        # Make sure numpy headers are included.
        if 'include_dirs' not in extension_kwargs:
            extension_kwargs['include_dirs'] = []
        extension_kwargs['include_dirs'].append(pybind11.get_include())

        if 'extra_compile_args' not in extension_kwargs:
            extension_kwargs['extra_compile_args'] = list()
        extension_kwargs['extra_compile_args'] += _EXTRA_COMPILE_ARGS

        if 'language' not in extension_kwargs:
            extension_kwargs['language'] = 'c++'

        # Create the extension module object.
        ext = Extension(mod_name, [mod_name_c], **extension_kwargs)

        # Clean.
        setup(ext_modules=[ext], script_args=['clean'])

        # Build and install the module.
        script_args = ['install', '--install-lib=' + mod_dir]
        if silent:
            script_args.append('--quiet')

        setup(ext_modules=[ext], script_args=script_args)

        module_filename = os.path.join(mod_dir, mod_name + _MOD_EXTENSION)
    finally:
        os.chdir(curpath)

    return module_filename
