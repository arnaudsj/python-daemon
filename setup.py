# -*- coding: utf-8 -*-

# Copyright © 2008–2009 Robert Niederreiter, Jens Klein, Ben Finney
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

from setuptools import setup, find_packages

version = '1.1.1'
shortdesc = u"Take a class and run it as a simple daemon."
longdesc = u""

setup(
    name='bda.daemon',
    version=version,
    description=shortdesc,
    long_description=longdesc,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Python Software Foundation License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules'        
        ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='Daemon Fork Unix',
    author='Robert Niederreiter',
    author_email='rnix@squarewave.at',
    url='http://svn.plone.org/svn/collective/bda.daemon',
    license='PSF',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['bda'],
    include_package_data=True,
    zip_safe=True,
    test_suite="tests.suite",
    install_requires=[
        'setuptools', 
        # -*- Extra requirements: -*
        ],
    extras_require={
        'test': [
            'minimock',
            ],
        },
    )
