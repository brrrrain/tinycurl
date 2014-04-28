#!/usr/bin/env python
from distutils.core import setup

setup(name='tinycurl',
      version='0.1',
      description='Simple cURL wrapper',
      author='Krab',
      author_email='krabbch@gmail.com',
      install_requires=['pycurl'],
      py_modules=['tinycurl', 'tinycurl_exceptions'])
