# -*- coding: utf-8 -*-

# Copyright © 2008–2009 Robert Niederreiter, Jens Klein, Ben Finney
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Python distribution setup
"""

import textwrap
from setuptools import setup, find_packages

import daemon as main_module

short_description, long_description = (
    textwrap.dedent(d).strip()
    for d in main_module.__doc__.split('\n\n', 1)
    )


setup(
    name='python-daemon',
    version=main_module.version,
    description=short_description,
    long_description=long_description,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Python Software Foundation License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules'
        ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='daemon fork unix',
    author='Ben Finney',
    author_email='ben+python@benfinney.id.au',
    url='http://pypi.python.org/pypi/python-daemon/',
    license='PSF',
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    zip_safe=False,
    test_suite="tests.suite",
    install_requires=[
        'setuptools',
        'lockfile >=0.7',
        ],
    tests_require=[
        'MiniMock >=1.0',
        ],
    )
