import pytest
from lightlab.util.inheritance import InheritanceBase, signatureRepr


class Mother(InheritanceBase):
    def __init__(self, mom=True, **kwargs):
        self.mom = mom
        super().__init__(**kwargs)

    def transmission(self, wl):
        return (2 * wl)

    def blip(self, a):
        return a+.1


class Father(InheritanceBase):
    def __init__(self, dad=True, **kwargs):
        self.dad = dad
        super().__init__(**kwargs)


class Child(Mother, Father):
    def transmission(self, b, x=1, **kwargs):
        ret = super().transmission(**kwargs)
        return (str(b), 10*x, kwargs['wl'], ret)


c = Mother()
d = Child()
def newb(x, y=2):
    pass


def test_inheritance():
    # Making sure that everything is init'ed appropriately
    e1 = Child()
    assert e1.mom and e1.dad
    e2 = Child(mom=False)
    assert not e2.mom and e2.dad
    e3 = Child(dad=False)
    assert e3.mom and not e3.dad
    e4 = Child(mom=False, dad=False)
    assert not e4.mom and not e4.dad

    strTests = []
    # String representations of functions
    strTests.append(('newb(x, y=2)',
        signatureRepr(newb)))
    strTests.append(('>>> newb >>>\n- Required: x\n-- Optional: y=2',
        signatureRepr(newb, True)))

    # Strings of methods
    strTests.append(('Child.transmission(b, x=1)',
        signatureRepr(d.transmission)))
    strTests.append(('>>> Child.transmission >>>\n- Required: b\n-- Optional: x=1',
        signatureRepr(d.transmission, True)))


    # Successful forms of inheritance
    assert d.blip(7) == c.blip(7) == 7.1
    assert Mother.transmission(c, 3) == c.transmission(3) == 6
    assert d.transmission(0, 10, wl=3) == ('0', 100, 3, 6)
    assert d.transmission(0, wl=3) == ('0', 10, 3, 6)

    # Error raising. These should give informative error messages
    answer = 'transmission() missing 1 required positional argument: \'wl\'\n'
    answer += signatureRepr(c.transmission, True) + '\n'
    answer += signatureRepr(d.transmission, True)
    with pytest.raises(TypeError) as err:
        d.transmission(b=2)
    strTests.append((answer, err.value.args[0]))

    answer = 'transmission() missing 1 required positional argument: \'b\'\n'
    answer += signatureRepr(d.transmission, True)
    with pytest.raises(TypeError) as err:
        d.transmission(wl=4)
    strTests.append((answer, err.value.args[0]))

    answer = 'transmission() got an unexpected keyword argument \'m\'\n'
    answer += signatureRepr(c.transmission, True) + '\n'
    answer += signatureRepr(d.transmission, True)
    with pytest.raises(TypeError) as err:
        d.transmission(b=1, wl=2, m=3)
    strTests.append((answer, err.value.args[0]))


    # Check all
    for trial in strTests:
        answer = trial[0]
        for attempt in trial[1:]:
            if answer != attempt:
                print('answer =', answer)
                print('attempt =', attempt)
                raise AssertionError

    # Done!
