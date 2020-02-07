''' Testing instrument getattr, setattr, delattr overloading. '''

import pytest
from lightlab.laboratory.instruments import Instrument
from lightlab.equipment.lab_instruments import VISAInstrumentDriver


class DerivedInstrument(Instrument):

    normal_variable = 'default'
    _private_variable = 'default_private'
    __superprivate_variable = 'default_superprivate'

    @property
    def private_variable(self):
        return self._private_variable

    @private_variable.setter
    def private_variable(self, value):
        self._private_variable = value

    @private_variable.deleter
    def private_variable(self):
        del self._private_variable

    @property
    def superprivate_variable(self):
        return self.__superprivate_variable

    @superprivate_variable.setter
    def superprivate_variable(self, value):
        self.__superprivate_variable = value

    @superprivate_variable.deleter
    def superprivate_variable(self):
        del self.__superprivate_variable


class ReDerivedInstrument(DerivedInstrument):
    pass


class NormalClass(object):

    normal_variable = 'default'
    _private_variable = 'default_private'
    __superprivate_variable = 'default_superprivate'

    @property
    def private_variable(self):
        return self._private_variable

    @private_variable.setter
    def private_variable(self, value):
        self._private_variable = value

    @private_variable.deleter
    def private_variable(self):
        del self._private_variable

    @property
    def superprivate_variable(self):
        return self.__superprivate_variable

    @superprivate_variable.setter
    def superprivate_variable(self, value):
        self.__superprivate_variable = value

    @superprivate_variable.deleter
    def superprivate_variable(self):
        del self.__superprivate_variable


class DerivedClass(NormalClass):
    pass


class BogusDriver(VISAInstrumentDriver):
    instrument_category = DerivedInstrument

    _write = ''

    def open(self):
        self.mbSession = 'open'

    def close(self):
        self.mbSession = None


def test_init():
    d = BogusDriver()
    assert d.__class__ == DerivedInstrument
    assert d._driver_class == BogusDriver
    assert d.driver.address is None


def test_address_change():
    d = BogusDriver(address='123')
    assert d.address == '123'
    assert d.driver.address == '123'
    d.driver.open()
    assert d.driver.mbSession == 'open'
    old_driver = d.driver
    d.address = '1234'
    assert d.driver is old_driver
    assert d.address == '1234'
    assert d.driver.address == '1234'
    assert d.driver.mbSession is None


# ### Compare DerivedInstrument's behavior with normal class
klasses = [NormalClass, DerivedClass, DerivedInstrument, ReDerivedInstrument]


@pytest.mark.parametrize("Klass", klasses)
def test_normal_variable(Klass):
    d = Klass()
    assert d.normal_variable == 'default'
    d.normal_variable = 123
    assert d.normal_variable == 123
    del d.normal_variable
    assert d.normal_variable == 'default'


@pytest.mark.parametrize("Klass", klasses)
def test_private_variable(Klass):
    d = Klass()
    assert d._private_variable == 'default_private'
    d._private_variable = 123
    assert d._private_variable == 123
    del d._private_variable
    assert d._private_variable == 'default_private'


@pytest.mark.parametrize("Klass", klasses)
def test_superprivate_variable(Klass):
    d = Klass()
    with pytest.raises(AttributeError):  # , message='should not be able to access __variable'
        assert d.__superprivate_variable == 'default_superprivate'
    d.__superprivate_variable = 123
    assert d.__superprivate_variable == 123
    del d.__superprivate_variable
    with pytest.raises(AttributeError):  # , message='should not be able to access __variable'
        assert d.__superprivate_variable == 'default_superprivate'


@pytest.mark.parametrize("Klass", klasses)
def test_unknownsuperprivate_variable(Klass):
    d = Klass()
    d.__unknownsuperprivate_variable = 123
    assert d.__unknownsuperprivate_variable == 123
    del d.__unknownsuperprivate_variable
    with pytest.raises(AttributeError):  # , message='should not be able to access __variable'
        assert print(d.__unknownsuperprivate_variable)


@pytest.mark.parametrize("Klass", klasses)
def test_property_private_variable(Klass):
    d = Klass()
    assert d.private_variable == 'default_private'
    d.private_variable = 123
    assert d.private_variable == 123
    del d.private_variable
    assert d.private_variable == 'default_private'


@pytest.mark.parametrize("Klass", klasses)
def test_property_superprivate_variable(Klass):
    d = Klass()
    assert d.superprivate_variable == 'default_superprivate'
    d.superprivate_variable = 123
    assert d.superprivate_variable == 123
    del d.superprivate_variable
    assert d.superprivate_variable == 'default_superprivate'
