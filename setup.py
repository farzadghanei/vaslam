#!/usr/bin/env python
"""
vaslam
"""
import os
from setuptools import setup, find_packages

from vaslam import __summary__, __version__, __author__, __license__

__all__ = ["setup_params", "classifiers", "long_description"]  # type: ignore

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: ISC License (ISCL)",
    "OPERATING SYSTEM :: POSIX :: LINUX",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Networking :: Monitoring",
]  # type: ignore


long_description = __summary__  # type: str

setup_params = dict(
    name="vaslam",
    packages=find_packages(),
    version=__version__,
    description=__summary__,
    long_description=long_description,
    author=__author__,
    url="https://github.com/farzadghanei/vaslam",
    license=__license__,
    classifiers=classifiers,
    test_suite="tests",
    zip_safe=True,
    entry_points=dict(console_scripts=["vaslam=vaslam.app:main",]),
)  # type: ignore


if __name__ == "__main__":
    setup(**setup_params)
