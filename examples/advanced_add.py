
import numpy as np
from pyinlinemodule import Cpp


@Cpp(verbose=False)
def advanced_add(a, b):
    __cpp__ = """
    return PyNumber_Add(a, b);
    """
    return a + b


if __name__ == '__main__':

    assert advanced_add(2, 3) == 5
    assert advanced_add(2.1, 3) == 2.1 + 3
    assert advanced_add(2.4, 3.2) == 2.4 + 3.2
    assert advanced_add([1, 2], [3, 4]) == [1, 2, 3, 4]
    assert advanced_add('hello ', 'world') == 'hello world'
