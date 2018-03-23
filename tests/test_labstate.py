'''Tests whether the functionality of the laboratory module is working properly.'''

import pytest
import lightlab.laboratory.state as labstate
from lightlab.laboratory.instruments import Host, Bench, Instrument, Keithley
from lightlab.laboratory.devices import Device
from lightlab.laboratory.experiments import Experiment, DualFunction
from lightlab.equipment.lab_instruments import Keithley_2400_SM
import json
import time
import os
import logging

logging.disable(logging.CRITICAL)
filename = 'test_{}.json'.format(int(time.time()))
labstate.filename = filename

# Shared objects
Host1 = Host(name="Host1")
Bench1 = Bench(name="Bench1")
Bench2 = Bench(name="Bench2")


def open_error(self):
    raise RuntimeError("self.open() function being called upon initialization.")


__GETCURRENTTEST = 0.123
Keithley_2400_SM.startup = lambda self: True
Keithley_2400_SM.getCurrent = lambda self: __GETCURRENTTEST
Keithley_2400_SM.open = open_error

instrument1 = Keithley(name="keithley1", bench=Bench1, host=Host1,
                       ports=["front_source", "rear_source"], _driver_class=Keithley_2400_SM)
instrument2 = Instrument(name="instrument2", bench=Bench1, host=Host1, ports=["port1", "channel"])
instrument2bis = Instrument(name="instrument2", bench=Bench2, host=Host1, ports=["port1", "channel"])
device1 = Device(name="device1", bench=Bench1, ports=["input", "output"])
device2 = Device(name="device2", bench=Bench1, ports=["input", "output"])


@pytest.fixture()
def lab(request):
    # The following instrument gets deleted over and over
    instrument2bis = Instrument(name="instrument2", bench=Bench2, host=Host1, ports=["port1", "channel"])
    lab = labstate.LabState(filename=filename)
    lab.updateHost(Host1)
    lab.updateBench(Bench1, Bench2)
    lab.insertInstrument(instrument1)
    lab.insertInstrument(instrument2)
    lab.insertInstrument(instrument2bis)  # still allows including two instruments with the same name
    lab.insertDevice(device1)
    lab.insertDevice(device2)

    connections1 = [{device1: "input", instrument1: "rear_source"},
                    {device1: "output", instrument2: "port1"}]
    lab.updateConnections(*connections1)
    lab._saveState(save_backup=False)

    def delete_file():
        os.remove(filename)
    request.addfinalizer(delete_file)
    return lab


def test_instantiate(lab):
    '''Initializing LabState with two instruments, devices, and interconnections,
    asserts if connections are properly made'''
    assert Bench1 in lab.benches.values()
    assert Host1 in lab.hosts.values()
    assert instrument1 in Bench1.instruments
    assert instrument1.bench == Bench1
    assert instrument1 in Host1.instruments
    assert instrument1.host == Host1
    assert instrument1 in lab.instruments
    assert instrument2bis in lab.instruments
    assert instrument2bis in Bench2.instruments
    assert instrument2bis in Host1.instruments
    assert device1 in lab.devices
    assert {device1: "input", instrument1: "rear_source"} in lab.connections
    assert {device1: "output", instrument2: "port1"} in lab.connections
    assert {device1: "input", instrument1: "front_source"} not in lab.connections
    assert {device1: "output", instrument2: "channel"} not in lab.connections


def test_delete(lab):
    b = instrument2bis.bench
    h = instrument2bis.host
    instrument2bis.bench = None
    instrument2bis.host = None
    assert instrument2bis not in b
    assert instrument2bis not in h
    assert instrument2bis not in lab.instruments


def test_savestate(lab):
    h1 = lab.hosts["Host1"]
    h1.mac_address = "test"
    lab.updateHost(h1)
    lab.saveState(filename, save_backup=False)


def test_reloadlabstate(lab):
    ''' Saves and reloads LabState and asserts equality '''

    lab2 = labstate.LabState.loadState(filename=filename)
    assert lab == lab2


def test_instrument_method_from_frozen(lab):
    lab2 = labstate.LabState.loadState(filename=filename)
    keithley = lab2.instruments_dict["keithley1"]
    assert keithley.getCurrent() == __GETCURRENTTEST


def test_corruptreload_extratext(lab):
    ''' Saves Labstate, corrupts JSON file, reloads from file, and test exception
    '''

    # Testing appending text to end
    with open(filename, 'a') as file:
        file.write("extra text")

    with pytest.raises(json.decoder.JSONDecodeError, message="fail to detect extraneous words outside JSON"):
        labstate.LabState.loadState(filename)


def test_corruptreload_changecontent(lab):
    ''' Saves Labstate, corrupts JSON file, reloads from file, and test exception
    '''

    # Testing changing json content
    with open(filename, 'r') as file:
        frozen_json = file.read()
        json_state = json.loads(frozen_json)
        json_state["py/state"]["benches"]["Bench1"]["py/state"]["name"] = "Bench2"
        refrozen_json = json.dumps(json_state, sort_keys=True, indent=4)
        with open(filename, 'w') as file:
            file.write(refrozen_json)
    with pytest.raises(RuntimeError, message="corruption within file was not detected"):
        labstate.LabState.loadState(filename)


def test_update_connections(lab):
    ''' Updates connections and test whether old connections are pruned
    '''
    # Changing ports in instrument
    change_connections = [{device1: "output", instrument2: "channel"}]
    lab.updateConnections(*change_connections)
    assert {device1: "output", instrument2: "port1"} not in lab.connections
    assert {device1: "output", instrument2: "channel"} in lab.connections

    # Changing instruments
    change_connections = [{device1: "output", instrument1: "front_source"}]
    lab.updateConnections(*change_connections)
    assert {device1: "output", instrument2: "channel"} not in lab.connections
    assert {device1: "output", instrument1: "front_source"} in lab.connections

    # Using invalid port (behavior: do not effect any change and throw error.)
    change_connections = [{device1: "output", instrument1: "front_sourcez"}]
    with pytest.raises(RuntimeError, message="unidentified port not detected"):
        lab.updateConnections(*change_connections)
    assert {device1: "output", instrument1: "front_sourcez"} not in lab.connections
    assert {device1: "output", instrument1: "front_source"} in lab.connections


def test_experiment_valid(lab):
    class TestExperiment(Experiment):
        warmed_up = None
        cooled_down = None

        def startup(self, lab):
            self.lab = lab
            self.registerInstruments(instrument1, instrument2, host=Host1, bench=Bench1)
            connections1 = [{device1: "input", instrument1: "rear_source"},
                            {device1: "output", instrument2: "port1"}]
            self.registerConnections(*connections1)

        def hardware_warmup(self):
            self.warmed_up = True
            self.cooled_down = False

        def hardware_cooldown(self):
            self.warmed_up = False
            self.cooled_down = True

        @DualFunction
        def test_func(self, x):
            return x ** 2

        @test_func.hardware
        def test_func(self, x):
            return x

    test_experiment = TestExperiment(lab=lab)

    with test_experiment.asVirtual():
        assert 16 == test_experiment.test_func(4)  # Testing virtualization

    assert test_experiment.valid

    # Testing hardware warmup and cooldown
    assert test_experiment.warmed_up is None
    assert test_experiment.cooled_down is None
    with test_experiment.asReal():
        assert test_experiment.warmed_up
        assert not test_experiment.cooled_down
        assert 4 == test_experiment.test_func(4)  # Testing hardware function
        with test_experiment.asVirtual():
            assert 16 == test_experiment.test_func(4)  # Testing temporary virtualization
        assert 4 == test_experiment.test_func(4)
    assert not test_experiment.warmed_up
    assert test_experiment.cooled_down


def test_experiment_invalid_connection(lab):
    class TestExperiment(Experiment):
        def startup(self, lab):
            self.lab = lab
            self.registerInstruments(instrument1, instrument2, host=Host1, bench=Bench1)
            connections1 = [{device1: "input", instrument1: "rear_source"},
                            {device1: "output", instrument2: "channel"}]
            self.registerConnections(*connections1)

    test_experiment = TestExperiment(lab=lab)
    assert not test_experiment.is_valid(reset=True)


def test_remove_instrument_by_name(lab):
    lab.deleteInstrumentFromName("instrument2")
    assert instrument2 in lab.instruments
    assert instrument2bis in lab.instruments
    lab.deleteInstrumentFromName("instrument2", force=True)
    assert instrument2 not in lab.instruments
    assert instrument2bis not in lab.instruments
