[![Actions Status](https://github.com/ahivert/tgtg-python/workflows/CI/badge.svg)](https://github.com/ahivert/tgtg-python/actions)
[![codecov](https://codecov.io/gh/ahivert/tgtg-python/branch/master/graph/badge.svg)](https://codecov.io/gh/ahivert/tgtg-python)

# tgtg-python

Python client that help you to talk with [TooGoodToGo](https://toogoodtogo.com) API.

Python version: 3.6, 3.7, 3.8

Handle:
- login
- list stores (`/item/`)
- get a store (`/item/<pk>`)

Used by:
- https://tgtg-notifier.com

## Install

For now, install it from github (it will be publish in PyPi)

```
pip install https://github.com/ahivert/tgtg-python/archive/master.zip
```

## Use it

```python
from tgtg import TgtgClient

# login with email and password
client = TgtgClient(email=your_email, password=your_password)

# or you can login with user_id and access_token
# (you can retrieve them from client after logged with email and password)
client = TgtgClient(access_token=your_access_token, user_id=your_user_id)

# You can then get items (as default it will get your favorites)
client.get_items()

# Or get an item
client.get_item(1234)

```

## Developers

This project use poetry so you will need to install locally poetry to use following
commands.
```
poetry install
```

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
