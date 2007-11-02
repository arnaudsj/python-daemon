# -*- coding: utf-8 -*-
#
# Copyright (c) 2006-2007 by:
#     Blue Dynamics Alliance
#         * Klein & Partner KEG, Austria
#         * Squarewave Computing Robert Niederreiter, Austria
#
# Permission to use, copy, modify, and distribute this software and its 
# documentation for any purpose and without fee is hereby granted, provided that 
# the above copyright notice appear in all copies and that both that copyright 
# notice and this permission notice appear in supporting documentation, and that 
# the name of Stichting Mathematisch Centrum or CWI not be used in advertising 
# or publicity pertaining to distribution of the software without specific, 
# written prior permission.
# 
# STICHTING MATHEMATISCH CENTRUM DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS 
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN 
# NO EVENT SHALL STICHTING MATHEMATISCH CENTRUM BE LIABLE FOR ANY SPECIAL, 
# INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS 
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER 
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF 
# THIS SOFTWARE.

"""
setup.py bdist_egg
"""

from setuptools import setup, find_packages
import sys, os

version = '1.0'

setup(
    name='bda.daemon',
    version=version,
    description="mixin to turn a class into a simple daemon.",
    long_description="""""",
    classifiers=[],
    keywords='daemon fork',
    author='Robert Niederreiter',
    author_email='dev@bluedynamics.com',
    url='http://svn.plone.org/svn/collective/bda.daemon',
    license='GPL',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['bda'],
    include_package_data=True,
    zip_safe=True,
)
