import json
from datetime import datetime, timezone
from decimal import Decimal


class JsonbToDict:
    @staticmethod
    def convert(value):
        return json.loads(value)


class TimestampzToAWSDateTime:
    @staticmethod
    def convert(value):
        return value.replace(' ', 'T') + 'Z'


class TimestampzToDatetimeUTC:
    @staticmethod
    def convert(value):
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


class NumericToDecimal:
    @staticmethod
    def convert(value):
        return Decimal(value)


GRAPHQL_CONVERTERS = {
    'jsonb': JsonbToDict,
    'timestamptz': TimestampzToAWSDateTime,
    'numeric': NumericToDecimal,
}
