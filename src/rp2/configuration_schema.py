# Copyright 2021 eprbell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

CONFIGURATION_SCHEMA = {
    "type": "object",
    "properties": {
        "in_header": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "integer",
                    "minimum": 0,
                },
                "asset": {
                    "type": "integer",
                    "minimum": 0,
                },
                "exchange": {
                    "type": "integer",
                    "minimum": 0,
                },
                "holder": {
                    "type": "integer",
                    "minimum": 0,
                },
                "transaction_type": {
                    "type": "integer",
                    "minimum": 0,
                },
                "spot_price": {
                    "type": "integer",
                    "minimum": 0,
                },
                "crypto_in": {
                    "type": "integer",
                    "minimum": 0,
                },
                "crypto_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "fiat_in_no_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "fiat_in_with_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "fiat_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "unique_id": {
                    "type": "integer",
                    "minimum": 0,
                },
                "notes": {
                    "type": "integer",
                    "minimum": 0,
                },
            },
            "required": [
                "timestamp",
                "asset",
                "exchange",
                "holder",
                "transaction_type",
                "spot_price",
                "crypto_in",
            ],
            "additionalProperties": False,
        },
        "out_header": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "integer",
                    "minimum": 0,
                },
                "asset": {
                    "type": "integer",
                    "minimum": 0,
                },
                "exchange": {
                    "type": "integer",
                    "minimum": 0,
                },
                "holder": {
                    "type": "integer",
                    "minimum": 0,
                },
                "transaction_type": {
                    "type": "integer",
                    "minimum": 0,
                },
                "spot_price": {
                    "type": "integer",
                    "minimum": 0,
                },
                "crypto_out_no_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "crypto_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "crypto_out_with_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "fiat_out_no_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "fiat_fee": {
                    "type": "integer",
                    "minimum": 0,
                },
                "unique_id": {
                    "type": "integer",
                    "minimum": 0,
                },
                "notes": {
                    "type": "integer",
                    "minimum": 0,
                },
            },
            "required": [
                "timestamp",
                "asset",
                "exchange",
                "holder",
                "transaction_type",
                "spot_price",
                "crypto_out_no_fee",
                "crypto_fee",
            ],
            "additionalProperties": False,
        },
        "intra_header": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "integer",
                    "minimum": 0,
                },
                "asset": {
                    "type": "integer",
                    "minimum": 0,
                },
                "from_exchange": {
                    "type": "integer",
                    "minimum": 0,
                },
                "from_holder": {
                    "type": "integer",
                    "minimum": 0,
                },
                "to_exchange": {
                    "type": "integer",
                    "minimum": 0,
                },
                "to_holder": {
                    "type": "integer",
                    "minimum": 0,
                },
                "spot_price": {
                    "type": "integer",
                    "minimum": 0,
                },
                "crypto_sent": {
                    "type": "integer",
                    "minimum": 0,
                },
                "crypto_received": {
                    "type": "integer",
                    "minimum": 0,
                },
                "unique_id": {
                    "type": "integer",
                    "minimum": 0,
                },
                "notes": {
                    "type": "integer",
                    "minimum": 0,
                },
            },
            "required": [
                "timestamp",
                "asset",
                "from_exchange",
                "from_holder",
                "to_exchange",
                "to_holder",
                "spot_price",
                "crypto_sent",
                "crypto_received",
            ],
            "additionalProperties": False,
        },
        "assets": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
            },
            "minItems": 1,
            "uniqueItems": True,
        },
        "exchanges": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
            },
            "minItems": 1,
            "uniqueItems": True,
        },
        "holders": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
            },
            "minItems": 1,
            "uniqueItems": True,
        },
    },
}
