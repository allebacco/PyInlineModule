
from pyinlinemodule import Cpp


@Cpp(verbose=True)
def compiled_function1(a):
    __cpp__ = """
    long a_value = PyLong_AsLong(a);
    return PyLong_FromLong(a_value + 5);
    """
    return a + 7



if __name__ == '__main__':

    result = compiled_function1(3)

    print('Result:', result)
