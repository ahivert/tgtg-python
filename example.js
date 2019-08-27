// item
// ####

// POST
// ====
{
    "discover": false,
    "favorites_only": true,
    "hidden_only": false,
    "origin": {
        "latLng": {
            "a": 0.0,
            "b": 0.0
        },
        "latitude": 0.0,
        "longitude": 0.0
    },
    "page": 1,
    "page_size": 100,
    "radius": 5000.0,
    "user_id": "1234",
    "with_stock_only": false
}

// Response
// ========
{
    "item": {
        "item_id": "123456",
        "price": {
            "code": "EUR",
            "minor_units": 399,
            "decimals": 2
        },
        "value": {
            "code": "EUR",
            "minor_units": 1200,
            "decimals": 2
        },
        "cover_picture": {
            "picture_id": "1234",
            "current_url": "https://images.tgtg.ninja/store/***_scale.jpg"
        },
        "logo_picture": {
            "picture_id": "4321",
            "current_url": "https://images.tgtg.ninja/store/***_scale.jpg"
        },
        "description": "",
        "category": "2",
        "favorite_count": 229
    },
    "store": {
        "store_id": "12345",
        "store_name": "Brioche Dorée",
        "description": "",
        "tax_identifier": "FR***********",
        "phone_number": "",
        "website": "https://www.briochedoree.fr/",
        "store_location": {
            "address": {
                "country": {
                    "iso_code": "FR",
                    "name": "France"
                },
                "address_line": "",
                "city": "",
                "postal_code": ""
            },
            "location": {
                "longitude": 0.0,
                "latitude": 0.0
            }
        },
        "logo_picture": {
            "picture_id": "1234",
            "current_url": "https://images.tgtg.ninja/store/***_scale.jpg"
        },
        "store_time_zone": "Europe/Paris",
        "hidden": false,
        "favorite_count": 0
    },
    "display_name": "Brioche Dorée",
    "display_description": "",
    "pickup_location": {
        "address": {
            "country": {
                "iso_code": "FR",
                "name": "France"
            },
            "address_line": "",
            "city": "",
            "postal_code": ""
        },
        "location": {
            "longitude": 0.0,
            "latitude": 0.0
        }
    },
    "items_available": 0,
    "distance": 0.0,
    "favorite": true,
    "in_sales_window": false,
    "new_item": false
}

