"""This file contains test for the examples of the package"""

import os
import pytest
import shutil
import subprocess


@pytest.mark.parametrize('ext', ['.py', '.sh'])
def test_complete_run(ext):
    folder = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'examples')
    script = os.path.join(folder, 'complete_run' + ext)
    assert os.path.isfile(script), script

    try:
        subprocess.check_call([script])
    finally:
        shutil.rmtree('./example_items', ignore_errors=True)
