import os
import tempfile
import atexit
import shutil
import glob
import stat


if 'PY_INLINE_TEMP' in os.environ:
    _PATH = os.environ['PY_INLINE_TEMP']
else:
    _PATH = tempfile.mkdtemp(prefix='pyinline_tmp_')

_EXTRA_COMPILE_ARGS = []
_MOD_EXTENSION = '.pyd'


# Remove the temporary directory at exit
def _cleanup_temp_folder(temp_dir):
    """Remove a directory tree"""
    os.chmod(temp_dir, stat.S_IWRITE)
    shutil.rmtree(temp_dir, ignore_errors=True)

atexit.register(_cleanup_temp_folder, _PATH)


if os.name == 'posix':
    # Compile args for Linux systems, in particular GCC
    _EXTRA_COMPILE_ARGS += ['-O3', '-march=native', '-std=c++11']
    _MOD_EXTENSION = '.so'
    _PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | \
        stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | \
        stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH

elif os.name == 'nt':
    # Compile args for Windows systems, in particular MSVC
    _EXTRA_COMPILE_ARGS = ['/O2', ' /GL-', '/MP', '/LTCG:OFF']
    _MOD_EXTENSION = '.pyd'
    _PERMISSIONS = stat.S_IWRITE | stat.S_IREAD

os.chmod(_PATH, _PERMISSIONS)


def extra_compile_args():
    """Extra compilation flags passed to the compiler
    """
    return _EXTRA_COMPILE_ARGS[::]


def set_extra_compile_args(compile_args):
    """Set the extra compilation flags passed to teh compiler

    Args:
        compile_args(list[str]): List of arguments for the compiler
    """
    global _EXTRA_COMPILE_ARGS
    _EXTRA_COMPILE_ARGS = list(compile_args)


def build_install_module(module_src, mod_name, extension_kwargs=None, module_dir=None, silent=True):
    """Build and install the compiled C Extension in the provided (or default) folder.

    Args:
        module_src(str): C++ source code of the module.
        mod_name(str): Name of the module.

    Keyword Args:
        extension_kwargs(dict): Extra arguments for the compilation of the extension module.
            Default ``None`` for no custom args.
        module_dir(str): Folder in which the module must be biult and installed. Default
            to a temporary folder.
        silent(bool): Disable verbosity logging. Default ``True``

    Returns:
        str,None: The filename of the compiled module or ``None`` if errors happens
            during compilation
    """

    # Save the current path so we can reset at the end of this function.
    curpath = os.getcwd()
    mod_name_c = mod_name + '.cpp'

    if module_dir is None:
        module_dir = str(_PATH)

    os.makedirs(module_dir, exist_ok=True)

    # Change to the code directory.
    os.chdir(module_dir)

    module_filename = None
    try:
        from setuptools import setup, Extension

        with open(mod_name_c, 'w') as module_cpp_file:
            # Write out the code.
            module_cpp_file.write(module_src)

        # Ensure the original extension_kwargs will not be modified
        if extension_kwargs is None:
            extension_kwargs = dict()
        else:
            extension_kwargs = extension_kwargs.copy()

        if 'extra_compile_args' not in extension_kwargs:
            extension_kwargs['extra_compile_args'] = list()
        extension_kwargs['extra_compile_args'] += _EXTRA_COMPILE_ARGS

        if 'language' not in extension_kwargs:
            extension_kwargs['language'] = 'c++'

        # Create the extension module object.
        ext = Extension(mod_name, [mod_name_c], **extension_kwargs)

        # Build and install the module.
        script_args = ['build', '--build-lib=' + module_dir]
        if silent:
            script_args.append('--quiet')
        else:
            script_args.append('--verbose')
        setup(ext_modules=[ext], script_args=script_args)

        path_to_search = os.path.join(module_dir, mod_name + '.*' + _MOD_EXTENSION)
        matched_files = glob.glob(path_to_search)
        if len(matched_files) != 1:
            raise RuntimeError("Unable to load the extension: matched files: %s" % str(matched_files))

        module_filename = matched_files[0]

        os.chmod(module_filename, _PERMISSIONS)
    except:
        if silent is False:
            import traceback
            traceback.print_exc()
    finally:
        os.chdir(curpath)

    return module_filename
