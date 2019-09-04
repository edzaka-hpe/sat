# Introduction

The Shasta Admin Toolkit (SAT) is a project to create a set of command-line
interfaces that cover gaps in the Shasta product which were identified by Cray
service and support staff. Various RESTful APIs currently exist in shasta, but
they return large amounts of data in a JSON format which is hard for admins and
service personnel to parse. We would like to provide CLIs that are more friendly
for human consumption.

This repository contains the python code implementing this CLI or set of CLIs.

# Installation

There are a few different ways that this software can be installed. At the
lowest level, this software is python code that implements a `setup.py` script
that uses `setuptools`. This level of installation is useful for the developer
who would like to quickly install and test changes in a python virtual
environment on a system.

In the product as the customer will see it, SAT is delivered as an RPM package.
The spec file in this repository uses the `setup.py` script in its build and
install sections to build and install in the RPM buildroot and generate the RPM.

This repository also includes an Ansible role named `cray_sat`. This role is
responsible for installing and configuring the SAT software on a Shasta system
within the installation framework that is based on Ansible. This role is
packaged into a crayctldeploy subpackage of cray-sat. This package will be
installed automatically by the Shasta installer, named `crayctl`. The `crayctl`
command will then include the `cray_sat` role at an appropriate stage of the
installer, which will result in the installation and configuration of the SAT
software.

## Installation via pip

To install, use `pip3`:

```
pip3 install $CHECKOUT_DIR
```

Where `$CHECKOUT_DIR` is the directory where the SAT repo is checked out.

To uninstall, use the following command:

```
pip3 uninstall sat
```
