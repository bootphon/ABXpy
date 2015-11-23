from ABXpy.misc.progress_display import ProgressDisplay
import time


def testProgressDisplay():
    d = ProgressDisplay()
    d.add('m1', 'truc 1', 12)
    d.add('m2', 'truc 2', 48)
    d.add('m3', 'truc 3', 24)

    for i in range(12):
        d.update('m1', 1)
        d.update('m2', 4)
        d.update('m3', 2)
        d.display()
        time.sleep(0.01)
