import os
import sys
import ABXpy.task
import warnings
import ConfigParser
import argparse
from tables import DataTypeWarning
from tables import NaturalNameWarning


version="0.2.1"


if getattr(sys, 'frozen', False):
    # frozen
    rdir = os.path.dirname(sys.executable)
else:
    # unfrozen
    rdir = os.path.dirname(os.path.realpath(__file__))
curdir = os.path.dirname(rdir)



class Discarder(object):
    def __init__(self):
        self.filt = "Exception RuntimeError('Failed to retrieve old handler',) in 'h5py._errors.set_error_handler' ignored"
        self.oldstderr = sys.stderr
        self.towrite = ''

    def write(self, text):
        self.towrite += text
        if '\n' in text:
            aux = []
            lines = text.split('\n')
            for line in lines:
                if line != self.filt and line != " ignored":
                    aux.append(line)
            self.oldstderr.write('\n'.join(aux))
            self.towrite = ''

    def flush(self):
        self.oldstderr.flush()

    def __exit__(self):
        self.oldstderr.write(self.towrite + '\n')
        #self.oldstderr.flush()
        sys.stderr = self.oldstderr


def parseConfig(configfile):
    taskslist = []
    config = ConfigParser.ConfigParser()
    assert os.path.exists(configfile), 'config file not found {}'.format(configfile)
    config.read(configfile)
    assert config.has_section('general'), 'general section missing in config file'
    general_items = dict(config.items('general'))
    sections = [section for section in config.sections() if section != 'general']
    for section in sections:
        task_items = dict(config.items(section))
        task_items['section'] = section
        for item in general_items:
            if item in task_items:
                warnings.warn('general config setting redefined in the task, the task specific one will be used ({}: {})'.format(item, task_items[item]), UserWarning)
            else:
                task_items[item] = general_items[item]
        taskslist.append(task_items)
    return taskslist


def lookup(attr, task_items, default=None):
    if attr in task_items:
        return task_items[attr]
    else:
        return default


def nonesplit(string):
    if string:
        return string.split()
    else:
        return None


def tryremove(path):
    try:
        os.remove(path)
    except:
        pass


def fullrun(task, verbose):
    taskfilename = os.path.join(curdir, lookup('taskfile', task))
    itemfilename = os.path.join(curdir, lookup('itemfile', task))
    tryremove(taskfilename)
    on = lookup('on', task)
    across = nonesplit(lookup('across', task))
    by = nonesplit(lookup('by', task))
    try:
        t = ABXpy.task.Task(itemfilename, on, across, by, verify=False, verbose=verbose)
        t.generate_triplets(output=taskfilename)
    except:
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare a corpus for the '
                                     'ABX discrimination task')

    parser.add_argument(
        '-c', '--corpus', choices=['sample', 'english', 'xitsonga', 'all',],
        default='all',
        help="corpus to prepare (default to all)")
    parser.add_argument(
        '-v', '--verbose',
        default=False,
        action='store_true',
        help="verbose flag")

    args = parser.parse_args()

    corpus = args.corpus

    sys.stderr = Discarder()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', NaturalNameWarning)
        warnings.simplefilter('ignore', DataTypeWarning)

        if corpus == 'sample' or corpus == 'all':
            config = os.path.join(curdir, 'resources/sample_eval.cfg')
            taskslist = parseConfig(config)
            for task in taskslist:
                fullrun(task, args.verbose)

        if corpus == 'english' or corpus == 'all':
            config = os.path.join(curdir, 'resources/english_eval.cfg')
            taskslist = parseConfig(config)
            for task in taskslist:
                fullrun(task, args.verbose)

        if corpus == 'xitsonga' or corpus == 'all':
            config = os.path.join(curdir, 'resources/xitsonga_eval.cfg')
            taskslist = parseConfig(config)
            for task in taskslist:
                fullrun(task, args.verbose)
