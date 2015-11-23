import h5py
import numpy as np
import os
import tempfile
from ABXpy.h5tools.h5_handler import H5Handler

# TODO some asserts...
def test_h5handler():
    # generate random h5 file
    n1 = 10
    n2 = 1000
    np.random.seed(42)
    folder = tempfile.mkdtemp()
    with h5py.File(os.path.join(folder, 'tmp.h5')) as fh:
        fh.create_group('key')
        fh['key'].create_dataset('k', (n2 * n1, 1), np.int64)
        fh.create_group('data')
        fh['data'].create_dataset('f', (n2 * n1, 3), np.float64)
        fh['data'].create_dataset('i', (n2 * n1, 5), np.int64)
        for i in range(n1):
            keys = np.random.randint(10 ** 12, size=(n2, 1))
            fh['key']['k'][i * n2:(i + 1) * n2, :] = keys
            floats = np.random.rand(n2, 3)
            fh['data']['f'][i * n2:(i + 1) * n2, :] = floats
            integers = np.random.randint(10 ** 12, size=(n2, 5))
            fh['data']['i'][i * n2:(i + 1) * n2, :] = integers

    #folder = '/var/folders/ma/maqYoEehEsiaVpQWYhnOr++++TY/-Tmp-/tmpaLxTaQ'
    # test sort on it
    h = H5Handler(
        os.path.join(folder, 'tmp.h5'), 'key', 'k', ['data', 'data'], ['f', 'i'])
    h.sort(100, 100)

    # get the same in a regular arrays and compare with regular sorting
    # ...
