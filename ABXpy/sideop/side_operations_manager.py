"""Class  providing services for task.py

- finds out the best point to execute side-operations (such as
  filtering and regressor generation) in the ABX task computation
  flow:

    * basically the more related a given side-operation is to the
      on/across/by structure of the ABX task, the earlier it can be
      executed and the lowest the computational cost is

- providing methods to actually carry out these side-operations at the
  point in the execution flow to which they were attributed

"""

import copy
import numpy as np


class SideOperationsManager(object):
    def __init__(self, db_hierarchy, on, across, by):
        # all columns
        self.extensions = ['', '_A', '_B', '_X', '_AB', '_AX', '_1', '_2']
        self.all_cols = {
            node.name for tree in db_hierarchy for node in tree.preOrder()}

        # FIXME add some checks that the original column names will
        # not cause parsing problems
        self.extended_cols = [
            col + ext for col in self.all_cols for ext in self.extensions]
        self.extended_cols_by_column = [
            [col + ext for col in self.all_cols] for ext in self.extensions]

        # find on/by/across descendant columns db_hierarchy is a list
        # of ABX.lib.tinytree object
        roots = [tree.findChild(lambda x: x.name == on[0])
                 for tree in db_hierarchy]
        for root in roots:
            if not(root is None):
                on_root = root
                break
        self.on_cols = {node.name for node in on_root.preOrder()}

        across_roots = []
        for col in across:
            roots = [tree.findChild(lambda x: x.name == col)
                     for tree in db_hierarchy]
            for root in roots:
                if not(root is None):
                    across_roots.append(root)
                    break

        self.across_cols = {col for root in across_roots for col in {
            node.name for node in root.preOrder()}}

        by_roots = []
        for col in by:
            roots = [tree.findChild(lambda x: x.name == col)
                     for tree in db_hierarchy]
            for root in roots:
                if not(root is None):
                    by_roots.append(root)
                    break

        self.by_cols = {col for root in by_roots for col in {
            node.name for node in root.preOrder()}}

        # other columns
        self.other_cols = set.difference(
            self.all_cols,
            set.union(self.on_cols, self.across_cols, self.by_cols))

        # FIXME containers could also add AX, AB, BX for further
        # optimization (but wait to see if this can really be useful)

        # one value for a whole 'by' database
        self.by = []

        # one value for a whole ABX cell
        self.on_across_by = []

        # value dependent on specific items in A column
        self.A = []

        # value dependent on specific items in B column (or on their
        # 'on' property which we do not treat as a special case as
        # there can be very few elements with the same 'on' in a row
        # in the B column)
        self.B = []

        # value dependent on specific items in X column (or on their
        # 'across' property which we do not treat as a special case as
        # there can be very few elements with the same 'across' in a
        # row in the X colum)
        self.X = []

        # most general case
        self.ABX = []

        self.by_context = {
            'by': set(),
            'generic': set(),
            'on_across_by': set(),
            'A': set(),
            'B': set(),
            'X': set(),
            'ABX': set()}

        self.generic_context = {'generic': set()}

        self.on_context = {
            'on_across_by': set(),
            'A': set(),
            'B': set(),
            'X': set(),
            'ABX': set()}

        self.across_context = {
            'on_across_by': set(),
            'A': set(),
            'B': set(),
            'X': set(),
            'ABX': set()}

        self.A_context = {'A': set(), 'ABX': set()}
        self.B_context = {'B': set(), 'ABX': set()}
        self.X_context = {'X': set(), 'ABX': set()}

    def parse_extended_columns(self, columns):
        """Get radical and suffix part for every context_variable, returns the
        set of the encountered couples.
        """
        out = set()
        for var in columns:
            out.add(self.parse_extended_column(var))
        return out

    def parse_extended_column(self, column):
        """Get radical and suffix part of a context_variable.
        """
        for i, cols in enumerate(self.extended_cols_by_column):
            if column in cols:
                suffix = self.extensions[i]
                radical = column[:len(column) - len(self.extensions[i])]
                break
        return radical, suffix

    def check_extensions(self, elements):
        """Check that something with a AX, AB or 1, 2 extension is an on/across
        descendant and a correct one for AX, AB.
        """
        errC1 = "_1 or _2"
        errC2 = "_AX"
        errC3 = "_AB"
        onAndAcross = "on and across"
        on = "on"
        across = "across"

        def valueError(column, attr):
            return ValueError("Columns used with extensions " + column + " in \
                              filter and regressor specifications must be \
                              appropriately determined by the " + attr + " of \
                              the task defined.")
        for r, s in elements:
            C1 = (s in ['_1', '_2'] and
                  not(r in self.on_cols or r in self.across_cols))
            C2 = s == '_AX' and not(r in self.across_cols)
            C3 = s == 'AB' and not(r in self.on_cols)
            if C1:
                raise valueError(errC1, onAndAcross)
            if C2:
                raise valueError(errC2, on)
            if C3:
                raise valueError(errC3, across)

    def classify_by(self, elements, db_fun, db_variables):
        """Detect operations that depend only on a variable that is used as a
        'by' factor in the ABX task.
        """
        # set db_variables
        db_variables['by'] = {(r, s) for r, s in elements if r in self.by_cols}
        # check if we have only by descendants (with or without extension) and
        # classify these as 'by'
        if {r for r, s in elements}.issubset(self.by_cols):
            self.by.append(db_fun)
            self.by_context['by'].update(db_variables['by'])
            elements = {}
        else:
            # columns determined by 'by' are not considered further
            elements = {(r, s) for r, s in elements if r not in self.by_cols}
        return elements, db_variables

    def classify_generic(self, elements, db_fun, db_variables):
        """Detect operations that can be applied directly to the columns of the
        original database. This is subclass specific...
        """
        return elements, db_variables

    # detect operations that can be applied at the level of an on/across/by
    # block during the generation of the ABX triplets
    def classify_on_across_by(self, elements, db_fun, db_variables):
        """Detect operations that can be applied at the level of an
        on/across/by block during the generation of the ABX triplets.
        """
        if '' in {s for r, s in elements}:
            radical = {r for (r, s) in elements if s == ''}
            raise ValueError('Use of column name(s) %s without extension is \
                            ambiguous in this context' % radical)
        else:
            # find elements that do not depend on _1, _AX, AB, or (A or X and
            # are descendants of on) or (A or B and are descendants of across)
            def condition(r, s):
                return (
                    not(s in ['_1', '_AX', '_AB'])
                    and not(s in ['_A', '_X'] and r in self.on_cols)
                    and not(s in ['A', 'B'] and r in self.across_cols))

            # fill db_variables
            db_variables['on'] = {(r, s) for r, s in elements if (
                not(condition(r, s)) and r in self.on_cols)}
            db_variables['across'] = {
                (r, s) for r, s in elements
                if (not(condition(r, s)) and r in self.across_cols)}

            elements = {e for e in elements if condition(e[0], e[1])}

            # if there are none, classify as on_across_by
            if not(elements):
                self.on_across_by.append(db_fun)
                self.by_context['on_across_by'].update(db_variables['by'])
                self.on_context['on_across_by'].update(db_variables['on'])
                self.across_context['on_across_by'].update(
                    db_variables['across'])
        return elements, db_variables

    # detect operations that depend on only one of the A, B or X
    # factors inside an on/across/by block other operations are
    # classified as ABX (the most general)
    def classify_ABX(self, elements, db_fun, db_variables):
        """the only left extensions are either not descendant of
        on/across/by or descendant of across and _X or descendant of
        on and _B (i.e. _2) we do not try to batch the _2 because we
        think they are potentially too small, instead if necessary we
        should batch several consecutive calls

        """
        # set up db_variables
        # FIXME could/should group these three contexts ???? + ABX ????
        # in the remaining elements _2 is considered as _B for a on descendant,
        # _X for a across descendant, so we only have remaining columns with
        # _A, _B or _X
        interpret_2 = lambda r: '_B' if r in self.on_cols else '_X'
        get_ext = lambda r, s: interpret_2(r) if s == '_2' else s
        db_variables['A'] = {(r, s)
                             for r, s in elements if get_ext(r, s) == '_A'}
        db_variables['B'] = {(r, s)
                             for r, s in elements if get_ext(r, s) == '_B'}
        db_variables['X'] = {(r, s)
                             for r, s in elements if get_ext(r, s) == '_X'}
        # if there is only _Xs or only _Bs, or only _As: classify as
        # 'singleton'
        exts = {get_ext(r, s) for r, s in elements}
        if exts == set(['_A']):
            self.A.append(db_fun)
            self.A_context['A'].update(db_variables['A'])
            name = 'A'
        elif exts == set(['_B']):
            self.B.append(db_fun)
            self.B_context['B'].update(db_variables['B'])
            name = 'B'
        elif exts == set(['_X']):
            self.X.append(db_fun)
            self.X_context['X'].update(db_variables['X'])
            name = 'X'
        # else: classify as 'triplet' (could also have pairs, but do not
        # implement until proved useful)
        else:
            self.ABX.append(db_fun)
            self.A_context['ABX'].update(db_variables['A'])
            self.B_context['ABX'].update(db_variables['B'])
            self.X_context['ABX'].update(db_variables['X'])
            name = 'ABX'
        self.by_context[name].update(db_variables['by'])
        self.on_context[name].update(db_variables['on'])
        self.across_context[name].update(db_variables['across'])

    # db_fun implements the dbfun API
    def add(self, db_fun, name=None):
        elements = self.parse_extended_columns(db_fun.input_names)
        db_variables = {}
        self.check_extensions(elements)
        # find appropriate point of execution for db_fun
        elements, db_variables = self.classify_by(
            elements, db_fun, db_variables)
        if elements:
            elements, db_variables = self.classify_generic(
                elements, db_fun, db_variables)
            if elements:
                elements, db_variables = self.classify_on_across_by(
                    elements, db_fun, db_variables)
                if elements:
                    self.classify_ABX(elements, db_fun, db_variables)

    # could use arrays instead of lists for speed ?
    def set_by_context(self, context, stage, by_values):
        for radical, extension in self.by_context[stage]:
            context[radical + extension] = [by_values[radical]]
        return context

    # could use arrays instead of lists for speed ?
    def set_generic_context(self, context, stage, db):
        for radical, extension in self.generic_context[stage]:
            # note that in the current implementation the extension is
            # always ''
            context[radical + extension] = list(db[radical])
        return context

    def set_on_across_context(self, context, stage, on_across_values):
        # this list contains 0 or 1 elements
        for radical, extension in self.on_context[stage]:
            context[radical + extension] = [on_across_values[radical]]
        for radical, extension in self.across_context[stage]:
            context[radical + extension] = [on_across_values[radical]]
        return context
    # FIXME use a single function for set_by and set_on and set_across ?

    def set_A_B_X_context(self, context_field, context, stage, db, indices):
        field = getattr(self, context_field)
        for radical, extension in field[stage]:
            # FIXME might be faster to index once for all the columns?
            context[radical + extension] = list(db[radical][indices])
        return context

    def set_ABX_context(self, context, db, triplets):
        # each column of triplets is redundant, this might be used to
        # acess the db more efficiently... this is the only call to
        # numpy in the module... could remove this if we always used
        # arrays...
        triplets = np.array(triplets)
        context = self.set_A_B_X_context(
            'A_context', context, 'ABX', db, triplets[:, 0])
        context = self.set_A_B_X_context(
            'B_context', context, 'ABX', db, triplets[:, 1])
        context = self.set_A_B_X_context(
            'X_context', context, 'ABX', db, triplets[:, 2])
        return context

    # the evaluate_... functions are actually generators to allow lazy
    # evaluation for filters
    def evaluate_by(self, by_values):
        context = self.set_by_context({}, 'by', by_values)  # set up context

        # evaluate dbfun
        return singleton_result_generator(self.by, context)

    # context passed as an argument can be used to induce side-effects
    # in the result generator, for example for lazy filter evaluation
    def evaluate_generic(self, by_values, db, context=None):
        # set up context
        if context is None:
            context = {}
        context = self.set_by_context(context, 'generic', by_values)
        for var in context:
            context[var] = context[var] * len(db)
        context = self.set_generic_context(context, 'generic', db)

        # evaluate dbfuns
        return result_generator(self.generic, context)

    # from this point on, by design, we are sure that generic
    # variables cannot be needed for context
    def evaluate_on_across_by(self, on_across_by_values):
        # set up context
        context = self.set_by_context({}, 'on_across_by', on_across_by_values)
        context = self.set_on_across_context(
            context, 'on_across_by', on_across_by_values)

        # evaluate dbfuns
        return singleton_result_generator(self.on_across_by, context)

    # possible optimization: group A, B, X context in case there is
    # some overlap ?
    def evaluate_A_B_X(self, name, on_across_by_values, db, indices,
                       context=None):
        # set up context. context passed as an argument can be used to
        # induce side-effects in the result generator, for example for
        # lazy filter evaluation
        if context is None:
            context = {}
        context = self.set_by_context(context, name, on_across_by_values)
        context = self.set_on_across_context(
            context, name,  on_across_by_values)
        for var in context:
            context[var] = context[var] * len(indices)
        context = self.set_A_B_X_context(
            name + '_context', context, name, db, indices)

        # evaluate dbfuns
        return result_generator(getattr(self, name), context)

    def evaluate_A(self, *args):
        return self.evaluate_A_B_X('A', *args)

    def evaluate_B(self, *args):
        return self.evaluate_A_B_X('B', *args)

    def evaluate_X(self, *args):
        return self.evaluate_A_B_X('X', *args)

    def evaluate_ABX(self, on_across_by_values, db, triplets, context=None):
        stage = 'ABX'

        # set up context. context passed as an argument can be used to
        # induce side-effects in the result generator, for example for
        # lazy filter evaluation
        if context is None:
            context = {}
        context = self.set_by_context(context, stage, on_across_by_values)
        context = self.set_on_across_context(
            context, stage, on_across_by_values)
        for var in context:
            context[var] = context[var] * len(triplets)
        context = self.set_ABX_context(context, db, triplets)

        # evaluate dbfuns
        return result_generator(getattr(self, stage), context)


def result_generator(db_funs, context):
    # to avoid any undesirable side-effects a deep-copy of the context is made
    # each time
    return (db_fun.evaluate(copy.deepcopy(context)) for db_fun in db_funs)


def singleton_result_generator(db_funs, context):
    # to avoid any undesirable side-effects a deep-copy of the context is made
    # each time
    return (db_fun.evaluate(copy.deepcopy(context))[0] for db_fun in db_funs)

# db_fun.evaluate returns [[np_array_output_1_dbfun_1,
# np_array_output_2_dbfun_1,...], [np_array_output_1_dbfun_2, ...],
# ...]
#
# Would the previous functions change with VLEN outputs that would
# change this pattern ?

# def test():
#     import ABX.lib.database
#     _, db_h = ABX.lib.database.load('../test/AI/corpus/AI.item')
#     som = SideOperationsManager(
#         db_h, ['consonant'], ['talker'], ['syllable_type', 'vowel'])
