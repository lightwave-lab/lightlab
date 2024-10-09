#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup, find_packages


LABSTATE_FILENAME = "labstate.json"
JUPYTER_GROUP = "jupyter"

# assert sys.version_info >= (3, 6), "Use python >= 3.6 - We are living in the __future__!"


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def main():
    with open('README.rst') as f:
        readme = f.read()

    with open('LICENSE') as f:
        license_text = f.read()

    with open("version.py") as f:
        code = compile(f.read(), "version.py", 'exec')
        version_dict = {}
        exec(code, {}, version_dict)  # pylint: disable=exec-used
        release = version_dict['release']

    metadata = dict(
        name='lightlab',
        version=release,
        description='Lightwave Lab instrument automation tools',
        long_description=readme,
        license=license_text.split('\n')[0],
        python_requires='>=3.6',
        packages=find_packages(exclude=('tests', 'docs', 'data')),
        url="https://github.com/lightwave-lab/lightlab",
        author="Alex Tait <atait@ieee.org>, Thomas Ferreira de Lima <tlima@princeton.edu>",
        author_email="tlima@princeton.edu",
        classifiers=(
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Topic :: Scientific/Engineering",
            "Topic :: System :: Hardware :: Hardware Drivers",
            "Framework :: Jupyter",
        ),
        install_requires=[
            'dpath',
            'jsonpickle',
            'matplotlib',
            'IPython',
            'PyVISA',
            'scipy',
            'scikit-learn',
            'dill',
        ],
        entry_points={
            'console_scripts': ['lightlab=lightlab.command_line:main'],
        }
    )

    setup(**metadata)


if __name__ == '__main__':
    main()
