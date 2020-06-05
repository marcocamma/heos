#!/usr/bin/env python

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="heos",
    version="0.1",
    packages = ["heos"],
    scripts=["bin/heos"],

    # metadata to display on PyPI
    author="Marco Cammarata",
    author_email="marcocamma@gmail.com",
    description="Control your HEOS system with python",
    long_description=long_description,
    long_description_content_type="text/markdown",    
    classifiers=[
        'Development Status :: 3 - Alpha',
        "License :: OSI Approved :: Python Software Foundation License"
    ],
    python_requires='>=3.6',
    include_package_data=True,

)
