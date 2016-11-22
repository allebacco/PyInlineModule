
from pyinlinemodule import Cpp


@Cpp(verbose=False)
def simple_add(a, b):
    __cpp__ = """
    long a_value = PyLong_AsLong(a);
    long b_value = PyLong_AsLong(b);
    return PyLong_FromLong(a_value + b_value);
    """
    return a + b


if __name__ == '__main__':

    assert simple_add(2, 3) == 5
    assert simple_add(2.1, 3) == 5
    assert simple_add(2.4, 3.2) == 5
