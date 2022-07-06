.. image:: https://github.com/techservicesillinois/farmit/workflows/CI/CD/badge.svg
   :target: https://github.com/techservicesillinois/farmit/actions?query=workflow%3ACI%2FCD
   :alt: Build Status

`farmit` is used to automate release management for projects using
Git and `setuptools_scm <https://github.com/pypa/setuptools_scm>`.

`farmit` creates and pushes a release branch off the default branch containing
a single commit with updates to the CHANGELOG.md file. The change information
is collected from commits since the last tag. Commits are expected
to have a title line followed by lines formatted as a markdown list:

This product is supported by the Cybersecurity Development team at the
University of Illinois, on a best-effort basis. As of the last update to
this README, the expected End-of-Life and End-of-Support dates of this
version are October of 2026, the same as its primary dependency
`Python V3.10 <https://www.python.org/dev/peps/pep-0619/#lifespan>`_.

.. |--| unicode:: U+2013   .. en dash
.. contents:: Jump to:
   :depth: 1

Installation
============

The simplest way to install `farmit` is to use pip::

    $ pip install farmit

Getting Started
===============

`farmit` creates and pushes a release branch off the default branch containing
a commit with updates to the CHANGELOG.md file. The change information
is collected from commits since the last tag. Commits are expected
to have a title line followed by lines formatted as a markdown list:

    Title line

    * Description 1
    * Description 2

    Fixes #1234

This example commit will appear as below in the CHANGELOG.md and
the release commit. Note that empty lines and lines containing
GitHub keywords, such as fixes, are removed:

+ Title line
  * Description 1
  * Description 2

Examples:
    farm micro
    farm 3.0.0
"""

Advanced Usage
==============

Command line arguments
======================

The plugin supports two subcommands `login`_ and `logout`_.

login
-----

options
```````

``--dry-run``
   Output generated update to CHANGELOG.md and stop.
``--verbose``
    Display verbose output. The flag can be repeated up to three
    times. Each time it is repeated more detailed information is
    returned.


configure
`````````

See `Getting Started`_ and online documentation for documentation on this
subcommand::

    $ aws login configure help

options
"""""""

``--verbose``
    Display verbose output. The flag can be repeated up to three
    times. Each time it is repeated more detailed information is
    returned.


logout
------

See `Getting Started`_ and online documentation for documentation on this
subcommand::

    $ aws logout help

options
```````

``--verbose``
    Display verbose output. The flag can be repeated up to three
    times. Each time it is repeated more detailed information is
    returned.
