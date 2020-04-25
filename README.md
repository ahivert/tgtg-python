[![Actions Status](https://github.com/ahivert/tgtg-python/workflows/CI/badge.svg)](https://github.com/ahivert/tgtg-python/actions)
[![codecov](https://codecov.io/gh/ahivert/tgtg-python/branch/master/graph/badge.svg)](https://codecov.io/gh/ahivert/tgtg-python)

# tgtg-python

Python client that help you to talk with [TooGoodToGo](https://toogoodtogo.com) API.

Python version: 3.6, 3.7, 3.8

Handle:
- login
- list stores (`/item/`)
- get a store (`/item/<pk>`)
- get all stores (`/index.php/api_tgtg/list_all_business_map_v5_gz`)

Used by:
- https://tgtg-notifier.com

## Install

```
pip install tgtg
```

## Use it

```python
from tgtg import TgtgClient

# login with email and password
client = TgtgClient(email=your_email, password=your_password)

# or you can login with user_id and access_token
# (you can retrieve them from client after logged with email and password)
client = TgtgClient(access_token=your_access_token, user_id=your_user_id)

# You can then get some items, default will get **only** your favorites
client.get_items()

# To get items (not only your favorites) you need to provide location informations
client.get_items(
    favorites_only=False,
    latitude=48.126,
    longitude=-1.723,
    radius=10,
)

# Or get an item
client.get_item(1234)

# get all items **without** auth (with limited fields, used for the map in the app)
client = TgtgClient()
client.get_all_business()

```

## Developers

This project use poetry so you will need to install locally poetry to use following
commands.
```
pip install poetry --user
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
