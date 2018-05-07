import os
from configparser import ConfigParser, NoSectionError
from pathlib import Path

user_config_dir = os.path.expanduser("~") + "/.lightlab"
user_config_path = user_config_dir + "/config.ini"
user_config_path = Path(user_config_path).resolve()

import argparse

parser = argparse.ArgumentParser(description="lightlab configuration tool")
parser.add_argument('command', type=str, choices=['labstate', 'config'],
                    metavar='<command>', help='config, labstate')
parser.add_argument('args', nargs=argparse.REMAINDER)


def main():
    args = parser.parse_args()
    if args.command == 'labstate':
        labstate_main(args.args)
    elif args.command == 'config':
        config_main(args.args)


labstate_parser = argparse.ArgumentParser()
labstate_parser.add_argument('--show', action='store_true',
                             help="show current labstate information")


def labstate_main(args):
    print("labstate", labstate_parser.parse_args(args))


config_cmd_parser = argparse.ArgumentParser(
    prog="lightlab config", formatter_class=argparse.RawTextHelpFormatter)
config_cmd_parser.add_argument('action', action='store', type=str,
                               help="write-default: write default configuration\n"
                                    "get [a.b [a2.b2]]: get configuration values\n"
                                    "set a.b c: set configuration value\n"
                                    "unset a.b: unset configuration value\n", nargs='?',
                               choices=("write-default", "get", "set", "unset"), metavar="command")
config_cmd_parser.add_argument('params', nargs=argparse.REMAINDER)


default_config = {"labstate": {'filepath': '~/.lightlab/labstate.json'}}


def write_default_config():
    config = ConfigParser()
    config.read_dict(default_config)
    with open(user_config_path, 'w') as user_config_file:
        config.write(user_config_file)


def get_config():
    if not os.path.isfile(user_config_path):
        os.makedirs(user_config_dir, exist_ok=True)
        user_config_path.touch()

    config = ConfigParser()
    config.read_dict(default_config)  # Read default first
    config.read(user_config_path)
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


def get_config_param(param, config):
    section, item = parse_param(param)
    if section is not None and item is not None:
        gotten_param = config.get(section, item)
        print(f"{section}.{item}: {gotten_param}")
    elif section is not None and item is None:
        for key, value in config[section].items():
            print(f"{section}.{key}: {value}")
    else:
        for section in config.sections():
            for key, value in config[section].items():
                print(f"{section}.{key}: {value}")
    return False


def config_main(args):
    config_args = config_cmd_parser.parse_args(args)
    params = config_args.params
    config = get_config()
    if config_args.action == 'write-default':
        write_default_config()
        print("Default config printed.")
    elif config_args.action == 'get':
        if len(params) > 0:
            for param in params:
                get_config_param(param, config)
        else:
            get_config_param(None, config)
    elif config_args.action == 'set':
        if len(params) == 2:
            param = params[0]
            set_value = params[1]
            section, item = parse_param(param)
            if section not in config:
                config[section] = {}
            config[section][item] = set_value
        else:
            raise RuntimeError(f"Invalid syntax. Use lightlab config set section.item value.")
        with open(user_config_path, 'w') as user_config_file:
            config.write(user_config_file)
    elif config_args.action == 'unset':
        if len(params) == 1:
            param = params[0]
            section, item = parse_param(param)
            if section and item:
                try:
                    success = config.remove_option(section, item)
                except NoSectionError:
                    success = False
            elif section:
                success = config.remove_section(section)
            print(f"{section}.{item} unset", "successfully" if success else "unsuccessfully")
        else:
            raise RuntimeError(f"Invalid syntax. Use lightlab config unset section.item")
        with open(user_config_path, 'w') as user_config_file:
            config.write(user_config_file)
    else:
        config_cmd_parser.print_help()
