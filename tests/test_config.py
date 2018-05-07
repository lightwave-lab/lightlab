import pytest
import time
import os
from pathlib import Path

from lightlab import config
from configparser import ConfigParser

filename = 'testconfig_{}.conf'.format(int(time.time()))
user_config_path = Path(filename).resolve()

default_config = config.default_config
default_config.update({"test_section": {"test_option": "test_value",
                                        "test_option2": "test_value2"}})


@pytest.fixture()
def config_default(request, monkeypatch):
    monkeypatch.setattr(config, 'user_config_path', user_config_path)

    def delete_file():
        if os.path.isfile(user_config_path):
            os.remove(user_config_path)
    request.addfinalizer(delete_file)


def test_get_config(config_default):
    # user_config_path should be nonexistent and stay nonexistent
    assert not os.path.isfile(user_config_path)
    config.get_config()
    assert not os.path.isfile(user_config_path)


def test_walk_default(config_default):
    config.write_default_config()
    conf = ConfigParser()
    conf.read(user_config_path)

    for section in default_config.keys():
        for item in default_config[section].keys():
            assert conf[section][item] == default_config[section][item]


def test_exceptions(config_default):
    with pytest.raises(config.InvalidSection, message="failed to detect invalid section"):
        config.get_config_param('invalid_section')
        config.print_config_param('invalid_section')

    first_section = next(iter(default_config.keys()))

    with pytest.raises(config.InvalidOption, message="failed to detect invalid option"):
        config.get_config_param(f"{first_section}.invalid_option")

    with pytest.raises(config.InvalidOption, message="failed to detect invalid option"):
        config.print_config_param(f"{first_section}.invalid_option")

    with pytest.raises(config.InvalidOption, message="failed to detect invalid option"):
        config.get_config_param(f"{first_section}")  # just the section


def test_print(config_default):
    """ Testing print function for command line tool."""
    first_section = next(iter(default_config.keys()))
    first_option = next(iter(default_config[first_section].keys()))
    config.print_config_param("")
    config.print_config_param(first_section)
    config.print_config_param(f"{first_section}.{first_option}")


def test_config_save(config_default):
    """ Testing configuration saving. Should not save non-default values"""
    conf = config.get_config()
    first_section = next(iter(default_config.keys()))
    first_option = next(iter(default_config[first_section].keys()))

    conf['new_section'] = {'new_option': 'new_value'}
    conf[first_section]['non_default_option'] = 'testing'
    config.config_save(conf)
    conf = ConfigParser()
    conf.read(user_config_path)

    assert 'new_section' in conf.sections()
    assert 'new_option' in conf['new_section']

    assert first_option not in conf[first_section].keys()  # not saving default values
    assert 'non_default_option' in conf[first_section].keys()
    assert conf[first_section]['non_default_option'] == 'testing'


def test_config_save_delete_default_section(config_default):
    conf = config.get_config()
    first_section = next(iter(default_config.keys()))
    config.config_save(conf)

    conf = ConfigParser()
    conf.read(user_config_path)
    assert first_section not in conf.sections()


def test_set_config_param(config_default):
    # should autosave
    config.set_config_param('labstate.filepath', 'blah')
    assert config.get_config_param('labstate.filepath') == 'blah'

    config.set_config_param('test_section.test_option', 'blah1')
    config.set_config_param('test_section.test_option2', 'blah2')
    assert config.get_config_param('test_section.test_option') == 'blah1'
    assert config.get_config_param('test_section.test_option2') == 'blah2'
    config.reset_config_param('test_section.test_option2')  # back to default

    # reset value of test_option2
    assert config.get_config_param('test_section.test_option2') == 'test_value2'
    config.reset_config_param('test_section')
    assert config.get_config_param('test_section.test_option') == 'test_value'


def execute(command):
    args = command.split(" ")
    return config.config_main(args)


def test_command_line(config_default, capsys):
    """ Testing normal usage of 'lightlab config' command line tool"""
    execute("get")  # should print all config variables
    captured1 = capsys.readouterr()
    assert "labstate.filepath: ~/.lightlab/labstate.json" in captured1.out

    execute("get labstate")
    captured1 = capsys.readouterr()
    assert "labstate.filepath: ~/.lightlab/labstate.json" in captured1.out

    execute("get labstate.filepath")
    captured1 = capsys.readouterr()
    assert "labstate.filepath: ~/.lightlab/labstate.json\n" == captured1.out

    with pytest.raises(RuntimeError, message="invalid syntax"):
        execute("set")

    with pytest.raises(config.InvalidOption, message="invalid syntax"):
        execute("set labstate 123")

    execute("set labstate.filepath 123")
    _ = capsys.readouterr()

    execute("get labstate.filepath")
    captured1 = capsys.readouterr()
    assert "labstate.filepath: 123\n" == captured1.out

    with pytest.raises(RuntimeError, message="invalid syntax"):
        execute("reset")

    with pytest.raises(RuntimeError, message="invalid syntax"):
        execute("reset labstate.filepath test_section")

    execute("reset labstate")
    _ = capsys.readouterr()

    execute("get labstate.filepath")
    captured1 = capsys.readouterr()
    assert "labstate.filepath: ~/.lightlab/labstate.json\n" == captured1.out

    execute("set labstate.filepath 123")
    _ = capsys.readouterr()

    execute("write-default")
    _ = capsys.readouterr()

    execute("get labstate.filepath")
    captured1 = capsys.readouterr()
    assert "labstate.filepath: ~/.lightlab/labstate.json\n" == captured1.out
