# Contributing

This document aims to outline steps and requirements for contribution to this project.

Contributions are subject to review via pull request.

## Developer Setup

Set your supported Python version. For example:

```sh
pyenv local 3.9.13
```

Create and activate a virtual environment:

```sh
python -m venv venv
source venv\bin\activate
```

Install the necessary dependencies:

```sh
make deps
```

Run the test suite to verify the environment is ready:

```sh
make test
```
