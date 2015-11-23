"""Read testing frozen files"""

import os

FROZEN_FOLDER = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'frozen_files')


def frozen_file(ext):
    return os.path.join(FROZEN_FOLDER, 'data') + '.' + ext
