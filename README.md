[![Actions Status](https://github.com/ahivert/tgtg-python/workflows/CI/badge.svg)](https://github.com/ahivert/tgtg-python/actions)
[![codecov](https://codecov.io/gh/ahivert/tgtg-python/branch/master/graph/badge.svg)](https://codecov.io/gh/ahivert/tgtg-python)
[![PyPI version](https://img.shields.io/pypi/v/tgtg?color=blue)](https://pypi.org/project/tgtg/)

# tgtg-python

Python client that help you to talk with [TooGoodToGo](https://toogoodtogo.com) API.

Python version: 3.9+

Handle:

- create an account (`/api/auth/vX/signUpByEmail`)
- login (`/api/auth/vX/authByEmail`)
- refresh token (`token/v1/refresh`)
- list stores (`/api/item/vX`)
- get a store (`/api/item/vX/:id`)
- get favorites (`/api/discover/vX/bucket`)
- set favorite (`/api/user/favorite/vX/:id/update`)
- create an order (`/api/order/vX/create/:id`)
- abort an order (`/api/order/vX/:id/abort`)
- get the status of an order (`/api/order/vX/:id/status`)
- get active orders (`/api/order/vX/active`)
- get inactive orders (`/api/order/vX/inactive`)

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
The client will wait until you validate the login by clicking the link inside the email.

Once you clicked the link, you will get credentials and be able to use them

```python
print(credentials)
{
    'access_token': '<your_access_token>',
    'refresh_token': '<your_refresh_token>',
    'cookie': '<cookie>',
}
```

### Build the client from tokens

```python
from tgtg import TgtgClient

client = TgtgClient(access_token="<access_token>", refresh_token="<refresh_token>", cookie="<cookie>")

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
            "item_price": {"code": "EUR", "minor_units": 499, "decimals": 2},
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

_(Using item_id from get_items response)_

```python
item = client.get_item(item_id=614318)
print(item)
```

<details>
<summary>Example response</summary>

```python
{
    "item": {
        "item_id": "614318",
        "sales_taxes": [{"tax_description": "TVA", "tax_percentage": 5.5}],
        "tax_amount": {"code": "EUR", "minor_units": 13, "decimals": 2},
        "price_excluding_taxes": {"code": "EUR", "minor_units": 236, "decimals": 2},
        "price_including_taxes": {"code": "EUR", "minor_units": 249, "decimals": 2},
        "value_excluding_taxes": {"code": "EUR", "minor_units": 0, "decimals": 2},
        "value_including_taxes": {"code": "EUR", "minor_units": 0, "decimals": 2},
        "taxation_policy": "PRICE_INCLUDES_TAXES",
        "show_sales_taxes": False,
        "cover_picture": {
            "picture_id": "620171",
            "current_url": "https://images.tgtg.ninja/item/cover/ac80c1b3-1386-46a8-ba80-c97b3a6e7e18.png",
            "is_automatically_created": False,
        },
        "logo_picture": {
            "picture_id": "622046",
            "current_url": "https://images.tgtg.ninja/store/6280890a-729c-400b-89d8-8b6d5b6cc17b.png",
            "is_automatically_created": False,
        },
        "name": "Panier petit déjeuner",
        "description": "Sauvez un panier-surprise réalisé à partir des délicieux articles d'un buffet petit déjeuner.",
        "food_handling_instructions": "",
        "can_user_supply_packaging": False,
        "packaging_option": "BAG_ALLOWED",
        "collection_info": "",
        "diet_categories": [],
        "item_category": "BAKED_GOODS",
        "buffet": True,
        "badges": [
            {
                "badge_type": "SERVICE_RATING_SCORE",
                "rating_group": "LOVED",
                "percentage": 96,
                "user_count": 131,
                "month_count": 6,
            },
            {
                "badge_type": "OVERALL_RATING_TRUST_SCORE",
                "rating_group": "LOVED",
                "percentage": 90,
                "user_count": 131,
                "month_count": 6,
            },
        ],
        "positive_rating_reasons": [
            "POSITIVE_FEEDBACK_FRIENDLY_STAFF",
            "POSITIVE_FEEDBACK_GREAT_QUANTITY",
            "POSITIVE_FEEDBACK_QUICK_COLLECTION",
            "POSITIVE_FEEDBACK_DELICIOUS_FOOD",
            "POSITIVE_FEEDBACK_GREAT_VALUE",
            "POSITIVE_FEEDBACK_GREAT_VARIETY",
        ],
        "average_overall_rating": {
            "average_overall_rating": 4.520325203252033,
            "rating_count": 123,
            "month_count": 6,
        },
        "allergens_info": {"shown_on_checkout": False},
        "favorite_count": 0,
    },
    "store": {
        "store_id": "624740",
        "store_name": "Hôtel Les Matins de Paris & Spa",
        "branch": "",
        "description": "Vous y êtes. Où ? À South Pigalle (Sopi pour les adeptes), au coeur d’une décontraction trendy.\nVous en êtes : de ceux qui ont déniché un lieu joliment habité, là où se fredonne depuis tant de décennies des airs vivement enjoués. Parce que, pour la petite histoire, notre adresse fut dans les années 50' 60' le repaire des plus arty.\nPile ici, le premier restaurant américain parisien créé par le fantaisiste Leroy Haynes attirait un heureux tohu-bohu, une kyrielle de musiciens, de Ray Charles à Marianne Faithfull…\nAujourd'hui, à vous d'improviser ici un rendez-vous amical, à vous de composer là avec la paresse la plus joyeuse. Se mettre au voluptueux diapason du spa, suivre le rythme des conseils spontanés d’une équipe concernée sont aussi des moments pour vous écouter.\nEntendez-vous la petite musique du lieu ? L'âme des Matins de Paris donne assurément le bon tempo pour prendre ses quartiers, les plus inspirés. ",
        "tax_identifier": "FR43552132029",
        "website": "https://www.lesmatinsdeparis.com/",
        "store_location": {
            "address": {
                "country": {"iso_code": "FR", "name": "France"},
                "address_line": "3 Rue Clauzel, 75009 Paris, France",
                "city": "",
                "postal_code": "",
            },
            "location": {"longitude": 2.3393925, "latitude": 48.8788434},
        },
        "logo_picture": {
            "picture_id": "622046",
            "current_url": "https://images.tgtg.ninja/store/6280890a-729c-400b-89d8-8b6d5b6cc17b.png",
            "is_automatically_created": False,
        },
        "store_time_zone": "Europe/Paris",
        "hidden": False,
        "favorite_count": 0,
        "items": [
            {
                "item": {
                    "item_id": "614318",
                    "sales_taxes": [{"tax_description": "TVA", "tax_percentage": 5.5}],
                    "tax_amount": {"code": "EUR", "minor_units": 13, "decimals": 2},
                    "price_excluding_taxes": {
                        "code": "EUR",
                        "minor_units": 236,
                        "decimals": 2,
                    },
                    "price_including_taxes": {
                        "code": "EUR",
                        "minor_units": 249,
                        "decimals": 2,
                    },
                    "value_excluding_taxes": {
                        "code": "EUR",
                        "minor_units": 0,
                        "decimals": 2,
                    },
                    "value_including_taxes": {
                        "code": "EUR",
                        "minor_units": 0,
                        "decimals": 2,
                    },
                    "taxation_policy": "PRICE_INCLUDES_TAXES",
                    "show_sales_taxes": False,
                    "cover_picture": {
                        "picture_id": "620171",
                        "current_url": "https://images.tgtg.ninja/item/cover/ac80c1b3-1386-46a8-ba80-c97b3a6e7e18.png",
                        "is_automatically_created": False,
                    },
                    "logo_picture": {
                        "picture_id": "622046",
                        "current_url": "https://images.tgtg.ninja/store/6280890a-729c-400b-89d8-8b6d5b6cc17b.png",
                        "is_automatically_created": False,
                    },
                    "name": "Panier petit déjeuner",
                    "description": "Sauvez un panier-surprise réalisé à partir des délicieux articles d'un buffet petit déjeuner.",
                    "food_handling_instructions": "",
                    "can_user_supply_packaging": False,
                    "packaging_option": "BAG_ALLOWED",
                    "collection_info": "",
                    "diet_categories": [],
                    "item_category": "BAKED_GOODS",
                    "buffet": True,
                    "badges": [
                        {
                            "badge_type": "SERVICE_RATING_SCORE",
                            "rating_group": "LOVED",
                            "percentage": 96,
                            "user_count": 131,
                            "month_count": 6,
                        },
                        {
                            "badge_type": "OVERALL_RATING_TRUST_SCORE",
                            "rating_group": "LOVED",
                            "percentage": 90,
                            "user_count": 131,
                            "month_count": 6,
                        },
                    ],
                    "positive_rating_reasons": [
                        "POSITIVE_FEEDBACK_FRIENDLY_STAFF",
                        "POSITIVE_FEEDBACK_GREAT_QUANTITY",
                        "POSITIVE_FEEDBACK_QUICK_COLLECTION",
                        "POSITIVE_FEEDBACK_DELICIOUS_FOOD",
                        "POSITIVE_FEEDBACK_GREAT_VALUE",
                        "POSITIVE_FEEDBACK_GREAT_VARIETY",
                    ],
                    "average_overall_rating": {
                        "average_overall_rating": 4.520325203252033,
                        "rating_count": 123,
                        "month_count": 6,
                    },
                    "favorite_count": 0,
                },
                "display_name": "Hôtel Les Matins de Paris & Spa (Panier petit déjeuner)",
                "pickup_interval": {
                    "start": "2022-11-04T11:00:00Z",
                    "end": "2022-11-04T15:00:00Z",
                },
                "pickup_location": {
                    "address": {
                        "country": {"iso_code": "FR", "name": "France"},
                        "address_line": "3 Rue Clauzel, 75009 Paris, France",
                        "city": "",
                        "postal_code": "",
                    },
                    "location": {"longitude": 2.3393925, "latitude": 48.8788434},
                },
                "purchase_end": "2022-11-04T15:00:00Z",
                "items_available": 0,
                "sold_out_at": "2022-11-03T17:11:32Z",
                "distance": 0.0,
                "favorite": True,
                "in_sales_window": True,
                "new_item": False,
            }
        ],
        "milestones": [
            {"type": "MEALS_SAVED", "value": "250"},
            {"type": "MONTHS_ON_PLATFORM", "value": "6"},
        ],
        "we_care": False,
        "distance": 0.0,
        "cover_picture": {
            "picture_id": "620171",
            "current_url": "https://images.tgtg.ninja/item/cover/ac80c1b3-1386-46a8-ba80-c97b3a6e7e18.png",
            "is_automatically_created": False,
        },
        "is_manufacturer": False,
    },
    "display_name": "Hôtel Les Matins de Paris & Spa (Panier petit déjeuner)",
    "pickup_interval": {"start": "2022-11-04T11:00:00Z", "end": "2022-11-04T15:00:00Z"},
    "pickup_location": {
        "address": {
            "country": {"iso_code": "FR", "name": "France"},
            "address_line": "3 Rue Clauzel, 75009 Paris, France",
            "city": "",
            "postal_code": "",
        },
        "location": {"longitude": 2.3393925, "latitude": 48.8788434},
    },
    "purchase_end": "2022-11-04T15:00:00Z",
    "items_available": 0,
    "sold_out_at": "2022-11-03T17:11:32Z",
    "distance": 0.0,
    "favorite": True,
    "in_sales_window": True,
    "new_item": False,
    "sharing_url": "https://share.toogoodtogo.com/download?locale=fr-FR",
    "next_sales_window_purchase_start": "2022-11-04T15:17:00Z",
}
```

</details>

## Create an order

```python
order = client.create_order(item_id, number_of_items_to_order)
print(order)
```

<details>
<summary>Example response</summary>

```python
{
  "id": "<order_id>",
  "item_id": "<item_id_that_was_ordered>",
  "state": "RESERVED",
  "order_line": {
    "quantity": 1,
    "item_price_including_taxes": {
      "code": "EUR",
      "minor_units": 600,
      "decimals": 2
    },
    "item_price_excluding_taxes": {
      "code": "EUR",
      "minor_units": 550,
      "decimals": 2
    },
    "total_price_including_taxes": {
      "code": "EUR",
      "minor_units": 600,
      "decimals": 2
    },
    "total_price_excluding_taxes": {
      "code": "EUR",
      "minor_units": 550,
      "decimals": 2
    }
  },
  "reserved_at": "2023-01-01T10:30:32.331280392",
  "order_type": "MAGICBAG"
}
```

</details>

Please note that payment of an order is currently not implemented.
In other words: you can create an order via this client, but you can not pay for it.

### Get the status of an order

```python
order_status = client.get_order_status(order_id)
print(order_status)
```

<details>
<summary>Example response</summary>

```python
{
  "id": "<order_id>",
  "item_id": "<item_id_that_was_ordered>",
  "state": "RESERVED"
}
```

</details>

### Abort an order

```python
client.abort_order(order_id)
```

When successful, this call will not return a value.

The app uses this call when the user aborts an order before paying for it. When the order has been payed, the app uses a different call.

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

### Get favorites

This will list all the currently set favorite stores.

```python
favorites = client.get_favorites()
print(favorites)
```

The behavior of `get_favorites` is more or less the same as `get_items()`, but better mimics the official application.

### Set favorite

_(Using item_id from get_items response)_

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
pipx install poetry
poetry install
```

This project uses [pre-commit](https://pre-commit.com/) to format/check all the
code before each commit automatically.

```
pipx install pre-commit
pre-commit install
```

Run this command to run all tests:

```
make test
```
