
from pyinlinemodule import cpp


@cpp
def compiled_function1(a):
    __cpp__ = """
    long a_value = PyLong_AsLong(a);
    return PyLong_FromLong(a_value + 5);
    """
    return a + 7


def test_cpp():

    assert compiled_function1(3) == 3 + 5
