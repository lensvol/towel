# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    description='A tool for API testing',
    name='towel',
    zip_safe=False,
    author='Ina Vasilevskaya',
    author_email='fernflower@gmail.com',
    url='https://github.com/fernflower/towel',
    version='0.1.0',
    install_requires=[
        'requests==2.6.0',
        'lxml==3.4.2',
    ],
    packages=['towel'],
    entry_points={
        'console_scripts': ['towel=towel.main:main']
    },
)
