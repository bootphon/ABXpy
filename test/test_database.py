"""This script tests the database.py file"""

import os
import pandas.core.frame
import pytest

import aux.generate as generate
import ABXpy.database.database as database

class TestDatabase:
    """Test of the database ABX module"""

    def setup(self):
        self.features_info = True
        self.filename = '/tmp/data.item'
        generate.items(2, 3, name=self.filename)
        self.db = database._load_database(self.filename)

    def teardown(self):
        try:
            os.remove(self.filename)
        except(OSError):
            pass

    def test_load_database(self):
        assert type(self.db) == pandas.core.frame.DataFrame

        assert ''.join(self.db.columns.tolist()).count('#') == 2
        assert self.db.columns[0][0] == '#'

        with pytest.raises(IOError):
            database._load_database('/path/to/no/where')

    def test_split_database_good(self):
        dba, dbf = database._split_database(self.db, self.filename,
                                            self.features_info)

        assert dba.columns.tolist() == ['item', 'c0', 'c1', 'c2']
        assert dbf.columns.tolist() == ['file', 'onset', 'offset']
        assert len(dba.index) == len(dbf.index) == 8

    def test_split_database_nofeatures1(self):
        with pytest.raises(ValueError):
            dba, dbf = database._split_database(self.db, self.filename, False)

    def test_split_database_nofeatures2(self):
        dba = database._split_database(self.db,self.filename, False)
        assert dba.columns.tolist() == ['item', 'c0', 'c1', 'c2']
        assert len(dba.index) == 8

    def test_split_database_badsharp1(self):
        db_bad = self.db.rename(columns={'#file': 'truc'})
        assert not db_bad.columns[0][0] == '#'

        with pytest.raises(IOError) as err:
            dba, dbf = database._split_database(db_bad, self.filename,
                                                self.features_info)
        assert 'The first column in' in str(err.value)

    def test_split_database_badsharp2(self):
        db_bad = self.db.rename(columns={'#item': 'truc'})
        assert ''.join(db_bad.columns.tolist()).count('#') == 1

        with pytest.raises(IOError) as err:
            dba, dbf = database._split_database(db_bad, self.filename,
                                                self.features_info)
        assert 'Exactly two columns in' in str(err.value)

    def test_split_database_badsharp3(self):
        db_bad = self.db.rename(columns={'c0':'#c0'})
        assert ''.join(db_bad.columns.tolist()).count('#') == 3

        with pytest.raises(IOError) as err:
            dba, dbf = database._split_database(db_bad, self.filename,
                                                self.features_info)
        assert 'Exactly two columns in' in str(err.value)
