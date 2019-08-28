[![Actions Status](https://github.com/ahivert/tgtg-python/workflows/CI/badge.svg)](https://github.com/ahivert/tgtg-python/actions)

# tgtg-python

Python client that help you to talk with TooGoodToGo API.

Handle:
- login
- list stores (`/item/`)

## Install

For now, install it from github (it will be publish in PyPi)

```
pip install https://github.com/ahivert/tgtg-python/archive/master.zip
```

## Developers

This project use poetry so you will need to install locally poetry to use following
commands.

This project use [black](https://github.com/psf/black) to format all the code,
[isort](https://github.com/timothycrosley/isort) to sort all imports and
lint is done by [flake8](https://github.com/PyCQA/flake8).

Just run this command to format automatically all the code you wrote:
```
make style
```

Run this command to run all tests:
```
make test
```