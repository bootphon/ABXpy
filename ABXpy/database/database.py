# make sure the rest of the ABXpy package is accessible
import os
import sys
package_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
if not(package_path in sys.path):
    sys.path.append(package_path)
# remove this dependency to ABXpy and create separate repository for this ?

import pandas
import numpy
import ABXpy.misc.tinytree as tinytree


# FIXME use just one isolated | as a separator instead of two #

# custom read_table that ignore empty entries at the end of a file (they
# can result from trailing white spaces at the end for example)
def read_table(filename):
    db = pandas.read_table(filename, sep='[ \t]+', engine='python')
    # removes row with all null values (None or NaN...)
    db = db.dropna(how='all')
    return db

# function that loads a database


def load(filename, features_info=False):
    # reading the main database using pandas (it is now a DataFrame)
    ext = '.item'
    if not(filename[len(filename) - len(ext):] == ext):
        filename = filename + ext
    db = read_table(filename)

    # finding '#' (to separate location info from attribute info) and fixing
    # names of columns
    columns = db.columns.tolist()
    l = []
    for i, c in enumerate(columns):
        if c[0] == "#":
            l.append(i)
            columns[i] = c[1:]
    db.columns = pandas.Index(columns)
    assert len(l) > 0 and l[
        0] == 0, ('The first column name in the database main file must be '
                  'prefixed with # (sharp)')
    assert len(
        l) == 2, ('Exactly two column names in the database main file must be'
                  ' prefixed with a # (sharp)')
    feat_db = db[db.columns[:l[1]]]
    db = db[db.columns[l[1]:]]
    # verbose print("  Read input File '"+filename+"'. Defined conditions:
    # "+str(newcolumns[attrI:len(columns)]))

    # opening up existing auxiliary files, and merging with the main database
    # and creating a forest describing the hierarchy at the same time (useful
    # for optimizing regressor generation and filtering)

    (basename, _) = os.path.splitext(filename)
    db, db_hierarchy = load_aux_dbs(basename, db, db.columns, filename)

    # dealing with missing items: for now rows with missing items are dropped
    nanrows = numpy.any(pandas.isnull(db), 1)
    if any(nanrows):
        dropped = db[nanrows]
        dropped.to_csv(basename + '-removed' + ext)
        db = db[~ nanrows]
    feat_db = feat_db[~ nanrows]
    # not so verbose print('** Warning ** ' + len(nanrows) + ' items were
    # removed because of missing information. The removed items are listed in'
    # + basename + '-removed.item'
    if features_info:
        return db, db_hierarchy, feat_db
    else:
        return db, db_hierarchy


# recursive auxiliary function for loading the auxiliary databases
def load_aux_dbs(basename, db, cols, mainfile):
    forest = [tinytree.Tree() for col in cols]
    for i, col in enumerate(cols):
        forest[i].name = col
        try:
            auxfile = basename + '.' + col
            if not(auxfile == mainfile):
                auxdb = read_table(auxfile)
                assert col == auxdb.columns[0], (
                    'First column name in file %s'
                    ' is %s. It should be %s instead.' % (
                        auxfile, auxdb.columns[0], col))
                # call get_aux_dbs on child columns
                auxdb, auxforest = load_aux_dbs(
                    basename, auxdb, auxdb.columns[1:])
                # add to forest
                forest[i].addChildrenFromList(auxforest)
                # merging the databases
                db = pandas.merge(db, auxdb, on=col, how='left')
        # verbose print("  Read auxiliary File '"+auxfile+"'. Defined
        # conditions: "+str(newcol[1:len(newcol)])+" on key '"+newcol[0]+"'")
        except IOError:
            pass
    return db, forest
