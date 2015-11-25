"""Provides the load() function for loading an ABX database from disk."""

import logging
import numpy
import os.path
import pandas
import tinytree


def load(filename, features_info=False):
    """Load an ABX database from its filename.

    An ABX database indexes the database on which the ABX task is
    executed.  See doc/FileFormat.rst for more details.

    Parameters:

    filename -- str. The file name of the ABX database to load.
    Following ABX conventions the extension of that file should be
    .item but this is not requested by the function.

    features_info -- bool. If True return features related columns
    from the database. False by default.

    Return:

    TODO

    Raise:

    IOError if the file cannot be loaded or is badly formatted.

    """
    # check the requested file exists
    if not os.path.isfile(filename):
        raise IOError('The file {} cannot be loaded'.format(filename))

    # load the database from pandas (can raise)
    db = _load_database(filename)

    # split database into features and attribute columns (can raise)
    if features_info:
        attribute_db, feature_db = _split_database(db, filename, True)
    else:
        attribute_db = _split_database(db, filename, False)

    logging.info('ABX database loaded from {}.'.format(filename))

    # merge existing auxiliary files with the main database. Create a
    # hierarchy at the same time (useful for optimizing regressors and
    # filters in ABX.task)
    attribute_db, db_hierarchy = _load_aux_databases(attribute_db, filename)

    # detecting missing items
    nan_rows = numpy.any(pandas.isnull(attribute_db), 1)
    is_nan = any(nan_rows)

    # TODO feature_db is not dropped. Should it be done?
    # TODO hierarchy is not updated, is it a bug?
    if is_nan:
        # suppress missing items in attributes
        attribute_db = attribute_db[~ nan_rows]

        # create a file for dropping
        (base, ext) = os.path.splitext(filename)
        drop_file = base + '-removed' + ext

        # drop them to a separate file.
        dropped = attribute_db[nan_rows]
        dropped.to_csv(drop_file)

        logging.warning('{} items were removed '.format(len(nanrows)) +
                        'because of missing information. The ' +
                        'removed items are listed in {}.'.format(drop_file))

    # removing missing items from feature_db if needed
    if features_info and is_nan:
        feature_db = feature_db[~ nan_rows]

    if features_info:
        return attribute_db, db_hierarchy, feature_db
    else:
        return attribute_db, db_hierarchy


def _load_database(filename):
    """Load the raw database with pandas.

    This function delegate loading to pandas.read_table(). Empty
    entries at the end of the file are ignored.

    Parameters:

    filename : str -- The file to load the database from.

    Return:

    The loaded database as a panda DataFrame.

    """
    # python engine specified to avoid a runtime warning
    db = pandas.read_table(filename, sep='[ \t]+', engine='python')

    # removes all null values (None or NaN...)
    db = db.dropna(how='all')

    return db


def _split_database(database, filename, features_info):
    """Split features columns from attribute columns in a database.

    This function parse the 1st line of the database and split it
    according to the position of the second '#' found in column
    names. Before that separator are features, after are attributes.

    Parameters:

    database : pandas.DataFrame -- The database to split.

    filename : str -- The file where the database was loaded
    from. This is usefull only for raising exceptions.

    features_info -- bool. If True return features related columns
    from the database.

    Return:

    The attribute columns of the database as a panda DataFrame. If
    features_info is True, also return the features columns, also as a
    DataFrame. Names of the columns are cleaned (with the '#'
    removed).

    Raise:

    IOError if the header line is badly formatted (if 1st column is
    not prefixed with '#' and if there is not exactly 2 columns
    begining with '#'.

    """
    # column titles as a str list
    columns = database.columns.tolist()

    # check for badly formatted titles
    if not columns[0][0] == '#':
        raise IOError('The first column in {}'.format(filename) +
                      ' must be prefixed with #')

    if not ''.join(columns).count('#') == 2:
        raise IOError('Exactly two columns in {}'.format(filename) +
                      ' must be prefixed with #')

    # find column indexes begining with '#'
    sharp_list = []
    for index, name in enumerate(columns):
        if name[0] == "#":
            sharp_list.append(index)
            columns[index] = name[1:]

    # rename columns with removed '#'
    database.columns = pandas.Index(columns)

    # split the database
    attribute_db = database[database.columns[sharp_list[1]:]]

    if features_info:
        feature_db = database[database.columns[:sharp_list[1]]]
        return attribute_db, feature_db
    else:
        return attribute_db


def _load_aux_databases(database, filename):
    """Load auxiliary databases.

    This function is a wrapper to _load_aux_databases_rec().

    """
    # filename with extension removed
    basename = os.path.splitext(filename)[0]

    # start the recursion
    database, forest = _load_aux_databases_rec(database, database.columns,
                                               filename, basename)

    return database, forest


# TODO document and test this function!
def _load_aux_databases_rec(database, columns, filename, basename):
    """Recursive function for loading auxiliary databases.

    """
    # Init an empty tree per column
    forest = [tinytree.Tree() for col in columns]

    for i, col in enumerate(columns):
        forest[i].name = col
        aux_file = basename + '.' + col

        # TODO replace try/except by os.path.isfile when tested
        try:
            if not aux_file == filename:
                aux_db = _load_database(aux_file)

                # TODO replace assert by raise
                assert col == aux_db.columns[0], (
                    'First column name in file {}'
                    ' is {}. It should be {} instead.'.format(
                        aux_file, aux_db.columns[0], col))

                # recursive call on child columns
                aux_db, aux_forest = _load_aux_databases_rec(
                    aux_db, aux_db.columns[1:], filename, basename)

                # add to forest
                forest[i].addChildrenFromList(aux_forest)

                # merging the databases
                database = pandas.merge(database, aux_db, on=col, how='left')

                logging.info('Read auxiliary file {}. '.format(aux_file) +
                             'Defined conditions {} on key {}.'.format(
                                 str(newcol[1:len(newcol)]), newcol[0]))
        except IOError:
            pass

    return database, forest
