#!/bin/env make -f
# license: ISC, see LICENSE for details.

SHELL = /bin/sh
makefile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
makefile_dir := $(dir $(makefile_path))
NAME=vaslam

# installation
DESTDIR ?=
prefix ?= /usr/local
exec_prefix ?= $(prefix)
bindir ?= $(exec_prefix)/bin

# use Make's builtin variable to call 'install'
INSTALL ?= install
INSTALL_PROGRAM ?= $(INSTALL)
INSTALL_DATA ?= $(INSTALL -m 644)


build:
	python setup.py build


test:
	tox

clean:
	python setup.py clean
	rm -rf $(NAME).egg-info
	rm -rf build
	find tests -type d -name '__pycache__' -exec rm -rf '{}' \; || true
	find vaslam -type d -name '__pycache__' -exec rm -rf '{}' \; || true

distclean: clean


install:
	python setup.py install

# requires python black formatter
format:
	black .


.DEFAULT_GOAL := build
.PHONY: build test clean distclean install format
