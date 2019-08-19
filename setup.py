#!/usr/bin/env python

from setuptools import find_packages, setup

import multifactor

setup(
    name='django-multifactor',
    version=multifactor.__version__,
    description='Drop-in multifactor authentication subsystem for Django.',
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author='Oli Warner',
    author_email='oli@thepcspy.com',
    url='https://github.com/oliwarner/django-multifactor',
    download_url='https://github.com/oliwarner/django-multifactor',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'django >= 2.2',
        'pyotp',
        'python-u2flib-server',
        'python-jose',
        'fido2 == 0.7',
    ],
    python_requires=">=3.5",
    include_package_data=True,
    zip_safe=False,  # because we're including static files
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 2.2",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)
