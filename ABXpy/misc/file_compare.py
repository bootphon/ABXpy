class AnalyzeFile(object):
    def __init__(self, csvfile):
        self.data = {}
        with open(csvfile) as csvin:
            for line in csvin:
                split = line.split()
                self.data[tuple(split[:-2])] = {'score': split[-2], 'n': split[-1]}


def distance_compare(distancefile1, distancefile2):
    return True


def score_compare(scorefile1, scorefile2):
    return True


def analyze_compare(csv1, csv2):
    return True
