'''Tests whether the functionality of the laboratory module is working properly.'''

import pytest
import lightlab.laboratory.state as labstate
from lightlab.laboratory.instruments import LocalHost, Host, Bench, Instrument, Keithley
from lightlab.laboratory.devices import Device
from lightlab.laboratory.experiments import Experiment
from lightlab.laboratory.virtualization import DualFunction
from lightlab.equipment.lab_instruments import Keithley_2400_SM
import json
import time
import os
import logging

logging.disable(logging.CRITICAL)
filename = 'test_{}.json'.format(int(time.time()))
labstate._filename = filename

# Shared objects
Host1 = LocalHost(name="Host1")
Host2 = Host(name="Host2")
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
device1 = Device(name="device1", bench=Bench1, ports=["input", "output"])
device2 = Device(name="device2", bench=Bench1, ports=["input", "output"])


@pytest.fixture()
def lab(request, monkeypatch):

    lab = labstate.LabState(filename=filename)
    lab.updateHost(Host1)
    lab.updateHost(Host2)
    lab.updateBench(Bench1, Bench2)
    lab.insertInstrument(instrument1)
    lab.insertInstrument(instrument2)
    lab.insertDevice(device1)
    lab.insertDevice(device2)

    connections1 = [{device1: "input", instrument1: "rear_source"},
                    {device1: "output", instrument2: "port1"}]
    lab.updateConnections(*connections1)
    lab._saveState(save_backup=False)
    monkeypatch.setattr(labstate, 'initializing', False)
    monkeypatch.setattr(labstate, 'lab', lab)

    def delete_file():
        os.remove(filename)
    request.addfinalizer(delete_file)
    return lab


def test_insert(lab):
    Bench1.addInstrument(instrument1, instrument2)
    assert instrument1 in Bench1
    assert instrument2 in Bench1
    with pytest.raises(TypeError, message="failed to detect wrong instrument type"):
        Bench1.addInstrument(device1)


def test_duplicate_insert(lab):
    instrument2bis = Instrument(name="instrument2", bench=Bench2, host=Host1, ports=["port11", "channel"])
    with pytest.raises(RuntimeError, message="duplicate insertion not detected"):
        lab.insertInstrument(instrument2bis)  # does not allow insertion of duplicate!


def test_instantiate(lab):
    '''Initializing LabState with two instruments, devices, and interconnections,
    asserts if connections are properly made'''
    assert Bench1 in lab.benches.values()
    assert Bench2 in lab.benches.values()
    assert len(lab.benches) == 2
    assert Host1 in lab.hosts.values()
    assert Host2 in lab.hosts.values()
    assert len(lab.hosts) == 2
    assert instrument1 in Bench1
    assert instrument1 in Bench1.instruments
    assert instrument1.bench == Bench1
    assert instrument1 in Bench1.instruments
    assert instrument1 in Host1.instruments
    assert instrument1.host == Host1
    assert instrument1 in lab.instruments
    assert instrument2 in lab.instruments
    assert instrument2 in Bench1
    assert instrument2 in Bench1.instruments
    assert len(lab.instruments) == 2
    assert device1 in lab.devices
    assert device1 in Bench1
    assert device2 in Bench1
    assert len(lab.devices) == 2
    assert {device1: "input", instrument1: "rear_source"} in lab.connections
    assert {device1: "output", instrument2: "port1"} in lab.connections
    assert {device1: "input", instrument1: "front_source"} not in lab.connections
    assert {device1: "output", instrument2: "channel"} not in lab.connections


def test_change_bench(lab):
    assert instrument2.bench == Bench1
    instrument2.bench = None
    assert instrument2 in lab.instruments
    assert instrument2 not in Bench1.instruments
    instrument2.bench = Bench2
    assert instrument2 in lab.instruments
    assert instrument2 in Bench2.instruments
    instrument2.bench = Bench1
    assert instrument2.bench == Bench1


def test_change_bench_alternative(lab):
    assert instrument2.bench == Bench1
    Bench2.addInstrument(instrument2)
    assert instrument2 in lab.instruments
    assert instrument2 in Bench2.instruments
    Bench2.removeInstrument(instrument2)
    assert instrument2 not in Bench2
    assert instrument2 in lab.instruments
    Bench1.addInstrument(instrument2)
    assert instrument2.bench == Bench1


def test_change_bench_device(lab):
    assert device2.bench == Bench1
    device2.bench = None
    assert device2 in lab.devices
    assert device2 not in Bench1.devices
    device2.bench = Bench2
    assert device2 in lab.devices
    assert device2 in Bench2.devices
    device2.bench = Bench1
    assert device2.bench == Bench1


def test_change_bench_device_alternative(lab):
    assert device2.bench == Bench1
    Bench2.addDevice(device2)
    assert device2 in lab.devices
    assert device2 in Bench2.devices
    Bench2.removeDevice(device2)
    assert device2 not in Bench2
    assert device2 in lab.devices
    Bench1.addDevice(device2)
    assert device2.bench == Bench1


def test_change_host(lab):
    assert instrument2.host == Host1
    instrument2.host = None
    assert instrument2 in lab.instruments
    assert instrument2 not in Host1.instruments
    instrument2.host = Host2
    assert instrument2 in lab.instruments
    assert instrument2 in Host2.instruments
    instrument2.host = Host1
    assert instrument2.host == Host1


def test_bench_iteration(lab):
    benches_items = []
    benches_names = []
    for bench_name, bench in lab.benches.items():
        device_names = [str(device) for device in bench.devices]
        instrument_names = [str(instrument) for instrument in bench.instruments]
        assert bench_name == bench.name
        benches_items.append(bench)
        benches_names.append(bench_name)

    benches_values = []
    for bench in lab.benches.values():
        benches_values.append(bench)
    assert benches_items == benches_values

    assert benches_names == [bench.name for bench in benches_values]


def test_display():
    Bench1.display()
    Bench2.display()
    Host1.display()
    Host2.display()
    instrument1.display()
    instrument2.display()
    device1.display()
    device2.display()


def test_delete(lab):
    lab.instruments.remove(instrument2)
    assert instrument2 not in lab.instruments


def test_savestate(lab):
    h1 = lab.hosts["Host1"]
    h1.mac_address = "test_savestate"
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
        json_state["py/state"]["benches"]["py/state"]["list"][0]["py/state"]["name"] = "Bench3"
        refrozen_json = json.dumps(json_state, sort_keys=True, indent=4)
        with open(filename, 'w') as file:
            file.write(refrozen_json)
    with pytest.raises(json.decoder.JSONDecodeError, message="corruption within file was not detected"):
        labstate.LabState.loadState(filename)


def test_update(lab):
    ''' Updates information on hosts, benches or instruments'''
    new_host2 = Host(name="Host2", hostname='foo')
    old_host2 = lab.hosts["Host2"]
    lab.hosts["Host2"] = new_host2
    assert lab.hosts["Host2"] == new_host2
    assert lab.hosts["Host2"] != old_host2  # old_host2 got de-referenced

    # WARNING! non-trivial effect true for hosts, benches and instruments:
    lab.hosts["Host3"] = new_host2  # this will rename new_host2 to "Host3"
    assert lab.hosts["Host3"] == new_host2
    assert new_host2.name == "Host3"
    assert lab.hosts["Host3"].name == "Host3"
    assert "Host2" not in lab.hosts.keys()

    del lab.hosts["Host3"]
    assert new_host2 not in lab.hosts


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
    assert len(lab.instruments) == 2
    lab.deleteInstrumentFromName("instrument2")
    assert instrument2 not in lab.instruments


def test_overwriting(lab):
    ''' Special cases when there are instrumentation_servers '''
    old_remote = Host2
    updated_remote = Host(name="Host2", foo=1)
    lab.updateHost(updated_remote)
    assert lab.hosts["Host2"] != old_remote
    assert lab.hosts["Host2"] == updated_remote

    old_server = Host1
    updated_server = LocalHost(name="Host1")
    updated_server.mac_address = 'test_overwriting'
    lab.updateHost(updated_server)  # should replace entry for 'Host1'
    assert lab.hosts["Host1"] != old_server
    assert lab.hosts["Host1"] == updated_server

    second_server = LocalHost(name="Another Host")
    lab.updateHost(second_server)
    assert lab.hosts["Host1"] == updated_server
    with pytest.raises(KeyError):
        lab.hosts["Another Host"]

def test_readonly(lab):
    instrument3 = Instrument(name="instrument3", bench=None, host=None, ports=["port11", "channel"])
    with pytest.raises(RuntimeError):        
        Host2.instruments.append(instrument3)
        Bench2.instruments.append(instrument3)
        Host1.instruments.dict['instrument1'] = instrument3
        Bench1.instruments.dict['instrument1'] = instrument3