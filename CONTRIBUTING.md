# Contributing

This document aims to outline steps and requirements for contribution to this project.

Contributions are subject to review via pull request.

## Developer Setup

Choose a supported Python version. For example:

```sh
cd <your cloned projects>/farmit
pyenv local 3.9.13
```

Create and activate a virtual environment:

```sh
cd <your cloned projects>/farmit
python -m venv venv
source venv\bin\activate
```

Install the necessary dependencies:

```sh
cd <your cloned projects>/farmit
make deps
```

Run the test suite to verify the environment is ready:

```sh
make test
```

## Developer Testing

Use `make shell` to setup a shell through `tox` with `farmit` on the path.

```sh
$ cd <your cloned projects>/farmit
$ make shell
... this takes a while on the first run...
... and produces a lot of output ...
$ which farmit
<your cloned projects>/farmit/.tox/wheel/bin/farmit
```
