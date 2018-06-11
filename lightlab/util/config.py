import os
import sys
from configparser import ConfigParser
from pathlib import Path
import argparse

user_config_path = os.path.expanduser("~") + "/.lightlab" + "/config.conf"
user_config_path = Path(user_config_path).resolve()

system_config_path = Path("/usr/local/etc/lightlab.conf")

default_config = {"labstate": {'filepath': '~/.lightlab/labstate.json'}}


def write_default_config():
    config = ConfigParser()
    config.read_dict(default_config)
    config_save(config, False)


def get_config():
    config = ConfigParser()
    config.read_dict(default_config)  # Read default first
    read_files = []
    if os.path.isfile(system_config_path):
        read_files.append(system_config_path)
    if os.path.isfile(user_config_path):
        read_files.append(user_config_path)
    if len(read_files) > 0:
        config.read(read_files)
    return config


def parse_param(param):
    if not param:
        return (None, None)
    split_param = param.split(".")
    section, item = None, None
    if len(split_param) > 0:
        section = split_param[0] if split_param[0] else None
    if len(split_param) > 1:
        item = split_param[1] if split_param[1] else None
    return (section, item)


class InvalidSection(RuntimeError):
    pass


class InvalidOption(RuntimeError):
    pass


def validate_param(section, option):
    if section is not None and section not in default_config.keys():
        raise InvalidSection(f"Unknown section {section}")
    if option is not None and option not in default_config[section].keys():
        raise InvalidOption(f"Unknown option {option}")
    if section is None or option is None:
        return False
    return True


def get_config_param(param):
    config = get_config()
    section, item = parse_param(param)
    if validate_param(section, item):
        return config.get(section, item)
    else:
        raise InvalidOption(param)


def print_config_param(param):
    config = get_config()
    section, item = parse_param(param)

    # raise exception if section or item are invalid
    validate_param(section, item)

    if section is not None and item is not None:
        gotten_param = get_config_param(param)
        print(f"{section}.{item}: {gotten_param}")
    elif section is not None and item is None:
        for key, value in config[section].items():
            print(f"{section}.{key}: {value}")
    else:
        for section in config.sections():
            for key, value in config[section].items():
                print(f"{section}.{key}: {value}")
    return False


def set_config_param(param, value):
    config = get_config()
    section, item = parse_param(param)
    if validate_param(section, item):
        config[section][item] = value
    else:
        raise InvalidOption(f"Cannot set '{param}'")
    config_save(config)
    return config


def reset_config_param(param):
    config = get_config()
    section, item = parse_param(param)
    validate_param(section, item)
    if section is not None and item is not None:
        config.remove_option(section, item)
        print(f"{section}.{item} reset.")
    elif section is not None and item is None:
        config.remove_section(section)
        print(f"{section}.* reset.")
    config_save(config)
    return config


def config_save(config, omit_default=True):
    """ Save config to a file. Omits default values if omit_default is True."""
    # remove all items that are default
    if omit_default:
        unset_items = []
        for section in config.sections():
            if section in default_config.keys():
                for option in config[section].keys():
                    if option in default_config[section].keys():
                        if config[section][option] == default_config[section][option]:
                            unset_items.append((section, option))
        for section, item in unset_items:
            config.remove_option(section, item)

        # remove all sections that are default
        unset_sections = []
        for section in config.sections():
            if len(config[section].keys()) == 0:
                unset_sections.append(section)
        for section in unset_sections:
            config.remove_section(section)

    if not os.path.isfile(user_config_path):
        os.makedirs(user_config_path.parent, exist_ok=True)
        user_config_path.touch()

    if not os.access(user_config_path, os.W_OK):
        print(f"Write permission to {user_config_path} denied. You cannot save. Try again with sudo.")
        return False
    with open(user_config_path, 'w') as user_config_file:
        config.write(user_config_file)
        print(f'----saving {user_config_path}----', file=sys.stderr)
        config.write(sys.stderr)
        print('----{}----'.format("-" * len(f"saving {user_config_path}")), file=sys.stderr)
    return True


config_cmd_parser = argparse.ArgumentParser(
    prog="lightlab config", formatter_class=argparse.RawTextHelpFormatter)
config_cmd_parser.add_argument('--system', action='store_true',
                               help='manipulate lightlab configuration for all users. run as root.')
config_cmd_parser.add_argument('action', action='store', type=str,
                               help="write-default: write default configuration\n"
                                    "get [a.b [a2.b2]]: get configuration values\n"
                                    "set a.b c: set configuration value\n"
                                    "reset a[.b]: unset configuration value\n", nargs='?',
                               choices=("write-default", "get", "set", "reset"), metavar="command")
config_cmd_parser.add_argument('params', nargs=argparse.REMAINDER)


def config_main(args):
    config_args = config_cmd_parser.parse_args(args)

    # If --system is set, change system_config_path
    if config_args.system:
        global user_config_path  # pylint: disable=W0603
        user_config_path = system_config_path
    elif os.getuid() == 0 and not os.environ.get('DOCKER'):
        raise SystemExit("Do not run as root except with --system flag.")

    params = config_args.params
    if config_args.action == 'write-default':
        write_default_config()
        print("Default config written.")
    elif config_args.action == 'get':
        if len(params) > 0:
            for param in params:
                print_config_param(param)
        else:
            print_config_param(None)
    elif config_args.action == 'set':
        if len(params) == 2:
            param = params[0]
            set_value = params[1]
            set_config_param(param, set_value)
        else:
            raise SystemExit(f"Invalid syntax. Use lightlab config set section.item value.")
    elif config_args.action == 'reset':
        if len(params) == 1:
            param = params[0]
            reset_config_param(param)
        else:
            raise SystemExit(f"Invalid syntax. Use lightlab config reset section[.item]")
    else:
        config_cmd_parser.print_help()
