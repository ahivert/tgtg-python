[![Actions Status](https://github.com/ahivert/tgtg-python/workflows/CI/badge.svg)](https://github.com/ahivert/tgtg-python/actions)
[![codecov](https://codecov.io/gh/ahivert/tgtg-python/branch/master/graph/badge.svg)](https://codecov.io/gh/ahivert/tgtg-python)
[![PyPI version](https://img.shields.io/pypi/v/tgtg?color=blue)](https://pypi.org/project/tgtg/)

# tgtg-python

Python client that help you to talk with [TooGoodToGo](https://toogoodtogo.com) API.

Python version: 3.6, 3.7, 3.8, 3.9

Handle:
- create an account (`auth/vX/signUpByEmail`)
- login (`/api/auth/vX/authByEmail`)
- refresh token (`/api/auth/vX/token/refresh`)
- list stores (`/api/item/`)
- get a store (`/api/item/:id`)
- set favorite (`/api/item/:id/setFavorite`)
- get active orders (`/api/order/vX/active`)
- get inactive orders (`/api/order/vX/inactive`)

Used by:
- https://tgtg-notifier.com

## Install

```
pip install tgtg
```

## Use it

### Retrieve tokens

Build the client with your email

```python
from tgtg import TgtgClient

client = TgtgClient(email="<your_email>")
credentials = client.get_credentials()
```

You should receive an email from tgtg. 
The will wait until you validate the login by clicking the link inside the email.

Once you clicked the link, you will get credentials and be able to use them

```python
print(credentials)
{
    'access_token': '<your_access_token>',
    'refresh_token': '<your_refresh_token>',
    'user_id': '<your_user_id>',
}
```



### Build the client from tokens

```python
from tgtg import TgtgClient

client = TgtgClient(access_token="<access_token>", refresh_token="<refresh_token>", user_id="<user_id>")

```

### Get items

```python
# You can then get some items, by default it will *only* get your favorites
items = client.get_items()
print(items)

# To get items (not only your favorites) you need to provide location informations
items = client.get_items(
    favorites_only=False,
    latitude=48.126,
    longitude=-1.723,
    radius=10,
)
print(items)
```

<details>
    <summary>Example response</summary>

```python
[
    {
        "item": {
            "item_id": "64346",
            "price": {"code": "EUR", "minor_units": 499, "decimals": 2},
            "sales_taxes": [],
            "tax_amount": {"code": "EUR", "minor_units": 0, "decimals": 2},
            "price_excluding_taxes": {"code": "EUR", "minor_units": 499, "decimals": 2},
            "price_including_taxes": {"code": "EUR", "minor_units": 499, "decimals": 2},
            "value_excluding_taxes": {
                "code": "EUR",
                "minor_units": 1500,
                "decimals": 2,
            },
            "value_including_taxes": {
                "code": "EUR",
                "minor_units": 1500,
                "decimals": 2,
            },
            "taxation_policy": "PRICE_INCLUDES_TAXES",
            "show_sales_taxes": False,
            "value": {"code": "EUR", "minor_units": 1500, "decimals": 2},
            "cover_picture": {
                "picture_id": "110628",
                "current_url": "https://images.tgtg.ninja/item/cover/2b69cbdd-43d3-4ade-bd51-50e338260859.jpg",
            },
            "logo_picture": {
                "picture_id": "110618",
                "current_url": "https://images.tgtg.ninja/store/fb893813-a775-4dec-ac7b-d4a7dd326fa8.png",
            },
            "name": "",
            "description": "Salva comida en Ecofamily Bufé y tu pack podrá contener: comidas caseras.",
            "can_user_supply_packaging": False,
            "packaging_option": "MUST_BRING_BAG",
            "collection_info": "",
            "diet_categories": [],
            "item_category": "MEAL",
            "badges": [
                {
                    "badge_type": "SERVICE_RATING_SCORE",
                    "rating_group": "LIKED",
                    "percentage": 93,
                    "user_count": 178,
                    "month_count": 5,
                }
            ],
            "favorite_count": 0,
            "buffet": False,
        },
        "store": {
            "store_id": "59949s",
            "store_name": "Ecofamily Bufé - Centro",
            "branch": "",
            "description": "",
            "tax_identifier": "",
            "website": "",
            "store_location": {
                "address": {
                    "country": {"iso_code": "ES", "name": "Spain"},
                    "address_line": "Av. de los Piconeros, S/N, 14001 Córdoba, España",
                    "city": "",
                    "postal_code": "",
                },
                "location": {"longitude": -4.776045, "latitude": 37.894249},
            },
            "logo_picture": {
                "picture_id": "110618",
                "current_url": "https://images.tgtg.ninja/store/fb893813-a775-4dec-ac7b-d4a7dd326fa8.png",
            },
            "store_time_zone": "Europe/Madrid",
            "hidden": False,
            "favorite_count": 0,
            "we_care": False,
        },
        "display_name": "Ecofamily Bufé - Centro",
        "pickup_location": {
            "address": {
                "country": {"iso_code": "ES", "name": "Spain"},
                "address_line": "Av. de los Piconeros, S/N, 14001 Córdoba, España",
                "city": "",
                "postal_code": "",
            },
            "location": {"longitude": -4.776045, "latitude": 37.894249},
        },
        "items_available": 0,
        "distance": 4241.995584076078,
        "favorite": True,
        "in_sales_window": False,
        "new_item": False,
    },
]
```
</details>

### Get an item
*(Using item_id from get_items response)*
```python
item = client.get_item(item_id=64346)
print(item)
```

<details>
<summary>Example response</summary>

```python
{
    "item": {
        "item_id": "64346",
        "price": {"code": "EUR", "minor_units": 499, "decimals": 2},
        "sales_taxes": [],
        "tax_amount": {"code": "EUR", "minor_units": 0, "decimals": 2},
        "price_excluding_taxes": {"code": "EUR", "minor_units": 499, "decimals": 2},
        "price_including_taxes": {"code": "EUR", "minor_units": 499, "decimals": 2},
        "value_excluding_taxes": {"code": "EUR", "minor_units": 1500, "decimals": 2},
        "value_including_taxes": {"code": "EUR", "minor_units": 1500, "decimals": 2},
        "taxation_policy": "PRICE_INCLUDES_TAXES",
        "show_sales_taxes": False,
        "value": {"code": "EUR", "minor_units": 1500, "decimals": 2},
        "cover_picture": {
            "picture_id": "110628",
            "current_url": "https://images.tgtg.ninja/item/cover/2b69cbdd-43d3-4ade-bd51-50e338260859.jpg",
        },
        "logo_picture": {
            "picture_id": "110618",
            "current_url": "https://images.tgtg.ninja/store/fb893813-a775-4dec-ac7b-d4a7dd326fa8.png",
        },
        "name": "",
        "description": "Salva comida en Ecofamily Buf\xc3\xa9 y tu pack podr\xc3\xa1 contener: comidas caseras.",
        "can_user_supply_packaging": False,
        "packaging_option": "MUST_BRING_BAG",
        "collection_info": "",
        "diet_categories": [],
        "item_category": "MEAL",
        "badges": [
            {
                "badge_type": "SERVICE_RATING_SCORE",
                "rating_group": "LIKED",
                "percentage": 93,
                "user_count": 178,
                "month_count": 5,
            }
        ],
        "favorite_count": 0,
        "buffet": False,
    },
    "store": {
        "store_id": "59949s",
        "store_name": "Ecofamily Buf\xc3\xa9 - Centro",
        "branch": "",
        "description": "",
        "tax_identifier": "",
        "website": "",
        "store_location": {
            "address": {
                "country": {"iso_code": "ES", "name": "Spain"},
                "address_line": "Av. de los Piconeros, S/N, 14001 C\xc3\xb3rdoba, Espa\xc3\xb1a",
                "city": "",
                "postal_code": "",
            },
            "location": {"longitude": -4.776045, "latitude": 37.894249},
        },
        "logo_picture": {
            "picture_id": "110618",
            "current_url": "https://images.tgtg.ninja/store/fb893813-a775-4dec-ac7b-d4a7dd326fa8.png",
        },
        "store_time_zone": "Europe/Madrid",
        "hidden": False,
        "favorite_count": 0,
        "items": [
            {
                "item": {
                    "item_id": "64346",
                    "price": {"code": "EUR", "minor_units": 499, "decimals": 2},
                    "sales_taxes": [],
                    "tax_amount": {"code": "EUR", "minor_units": 0, "decimals": 2},
                    "price_excluding_taxes": {
                        "code": "EUR",
                        "minor_units": 499,
                        "decimals": 2,
                    },
                    "price_including_taxes": {
                        "code": "EUR",
                        "minor_units": 499,
                        "decimals": 2,
                    },
                    "value_excluding_taxes": {
                        "code": "EUR",
                        "minor_units": 1500,
                        "decimals": 2,
                    },
                    "value_including_taxes": {
                        "code": "EUR",
                        "minor_units": 1500,
                        "decimals": 2,
                    },
                    "taxation_policy": "PRICE_INCLUDES_TAXES",
                    "show_sales_taxes": False,
                    "value": {"code": "EUR", "minor_units": 1500, "decimals": 2},
                    "cover_picture": {
                        "picture_id": "110628",
                        "current_url": "https://images.tgtg.ninja/item/cover/2b69cbdd-43d3-4ade-bd51-50e338260859.jpg",
                    },
                    "logo_picture": {
                        "picture_id": "110618",
                        "current_url": "https://images.tgtg.ninja/store/fb893813-a775-4dec-ac7b-d4a7dd326fa8.png",
                    },
                    "name": "",
                    "description": "Salva comida en Ecofamily Buf\xc3\xa9 y tu pack podr\xc3\xa1 contener: comidas caseras.",
                    "can_user_supply_packaging": False,
                    "packaging_option": "MUST_BRING_BAG",
                    "collection_info": "",
                    "diet_categories": [],
                    "item_category": "MEAL",
                    "badges": [
                        {
                            "badge_type": "SERVICE_RATING_SCORE",
                            "rating_group": "LIKED",
                            "percentage": 93,
                            "user_count": 178,
                            "month_count": 5,
                        }
                    ],
                    "favorite_count": 0,
                    "buffet": False,
                },
                "display_name": "Ecofamily Buf\xc3\xa9 - Centro",
                "pickup_location": {
                    "address": {
                        "country": {"iso_code": "ES", "name": "Spain"},
                        "address_line": "Av. de los Piconeros, S/N, 14001 C\xc3\xb3rdoba, Espa\xc3\xb1a",
                        "city": "",
                        "postal_code": "",
                    },
                    "location": {"longitude": -4.776045, "latitude": 37.894249},
                },
                "items_available": 0,
                "distance": 0.0,
                "favorite": True,
                "in_sales_window": False,
                "new_item": False,
            }
        ],
        "milestones": [
            {"type": "MEALS_SAVED", "value": "500"},
            {"type": "MONTHS_ON_PLATFORM", "value": "6"},
        ],
        "we_care": False,
    },
    "display_name": "Ecofamily Buf\xc3\xa9 - Centro",
    "pickup_location": {
        "address": {
            "country": {"iso_code": "ES", "name": "Spain"},
            "address_line": "Av. de los Piconeros, S/N, 14001 C\xc3\xb3rdoba, Espa\xc3\xb1a",
            "city": "",
            "postal_code": "",
        },
        "location": {"longitude": -4.776045, "latitude": 37.894249},
    },
    "items_available": 0,
    "distance": 0.0,
    "favorite": True,
    "in_sales_window": False,
    "new_item": False,
}

```

</details>

### Get active orders

```python
active = client.get_active()
print(active)
```

### Get inactive orders

```python
client.get_inactive(page=0, page_size=20)

# returned object has `has_more` property if more results are available
```

To e.g. sum up all orders you have ever made:

```python
    orders = []
    page = 0
    while inactive := client.get_inactive(page=page, page_size=200):
        orders += inactive["orders"]
        if not inactive["has_more"]:
            break

    redeemed_orders = [x for x in orders if x["state"] == "REDEEMED"]
    redeemed_items = sum([x["quantity"] for x in redeemed_orders])

    # if you bought in multiple currencies this will need improvements
    money_spend = sum(
        [
            x["price_including_taxes"]["minor_units"]
            / (10 ** x["price_including_taxes"]["decimals"])
            for x in redeemed_orders
        ]
    )

    print(f"Total numbers of orders: {len(orders)}")
    print(f"Total numbers of picked up orders: {len(redeemed_orders)}")
    print(f"Total numbers of items picked up: {redeemed_items}")
    print(
        f"Total money spend: ~{money_spend:.2f}{redeemed_orders[0]['price_including_taxes']['code']}"
    )
```


### Set favorite
*(Using item_id from get_items response)*

```python
# add favorite
client.set_favorite(item_id=64346, is_favorite=True)

# remove favorite
client.set_favorite(item_id=64346, is_favorite=False)
```

### Create an account

```python
from tgtg import TgtgClient

client = TgtgClient()
client.signup_by_email(email="<your_email>")

# client is now ready to be used
```

## Developers

This project uses poetry so you will need to install poetry locally to use following
commands.
```
pip install poetry --user
poetry install
```

This project uses [pre-commit](https://pre-commit.com/) to format/check all the
code before each commit automatically.
```
pip install pre-commit --user
pre-commit install
```

Run this command to run all tests:
```
make test
```
