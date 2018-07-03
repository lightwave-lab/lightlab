from lightlab.equipment.abstract_drivers import MultiModalSource
import pytest


@pytest.mark.parametrize("mode", list(MultiModalSource.supportedModes))
def test_inverse_val2base(mode):
    baseunit_val = sum(MultiModalSource.baseUnitBounds) / 2
    newvalue = MultiModalSource.baseUnit2val(baseunit_val, mode)
    baseunit = MultiModalSource.val2baseUnit(newvalue, mode)
    assert baseunit_val == baseunit
