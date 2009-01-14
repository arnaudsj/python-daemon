# Copyright (c) 2008-2009 Robert Niederreiter, Jens Klein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from setuptools import setup, find_packages

version = '1.1.1'
shortdesc = u"Take a class and run it as a simple daemon."
longdesc = u""

setup(name='bda.daemon',
      version=version,
      description=shortdesc,
      long_description=longdesc,
      classifiers=[
            'Development Status :: 5 - Production/Stable',
            'License :: OSI Approved :: MIT License',
            'Operating System :: POSIX',
            'Programming Language :: Python',
            'Intended Audience :: Developers',
            'Topic :: Software Development :: Libraries :: Python Modules'        
      ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='Daemon Fork Unix',
      author='Robert Niederreiter',
      author_email='rnix@squarewave.at',
      url='http://svn.plone.org/svn/collective/bda.daemon',
      license='MIT',
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
          ]
      })
