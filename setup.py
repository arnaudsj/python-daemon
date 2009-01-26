# -*- coding: utf-8 -*-

# Copyright © 2008–2009 Robert Niederreiter, Jens Klein, Ben Finney
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

from setuptools import setup, find_packages

version = '1.2'
shortdesc = u"Library to implement a well-behaved Unix daemon process"
longdesc = u"""
    This library implements PEP [no number yet], Standard daemon
    process library.
    """

setup(
    name='python-daemon',
    version=version,
    description=shortdesc,
    long_description=longdesc,
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
        ],
    tests_require=[
        'MiniMock >=1.0',
        ],
    )
