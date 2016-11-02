
from pyinlinemodule import cpp


@cpp
def compiled_function1(a):
    __cpp__ = """
    py::int_ var = py::int_(a) + 5;
    var.inc_ref();
    return var.ptr();
    """
    return a + 7


def test_cpp():

    assert compiled_function1(3) == 3 + 5
