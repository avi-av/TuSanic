"""
TuSanic
-------------

Implements the tus.io server-side file-upload protocol
visit http://tus.io for more information

The project code is based on the code written by @matthoskins1980
"""
from setuptools import setup, find_packages


setup(
    name='TuSanic',
    version='0.1.0.dev1',
    url='https://github.com/avi-av/TuSanic.git',
    license='MIT',
    author='Avi_av',
    description='TUS protocol implementation for sanic',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'sanic',
        'pony',
        'loguru'
    ],
    python_requires='>=3.6',
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
