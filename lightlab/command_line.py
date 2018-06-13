import argparse
from lightlab.util.config import config_main

version = '1.0.2'

parser = argparse.ArgumentParser(description="lightlab configuration tool")
parser.add_argument('command', type=str, choices=['labstate', 'config'],
                    metavar='<command>', help='config, labstate')
parser.add_argument('args', nargs=argparse.REMAINDER)
parser.add_argument('-v', '--version', action='version', version=f'%(prog)s v{version}')


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
    print(f"labstate feature not yet implemented (args = {args})")
