import json
from datetime import datetime, timezone, date
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
        padded = value.ljust(26, '0') if (len(value)) > 19 else value
        return datetime.fromisoformat(padded).replace(tzinfo=timezone.utc)


class DateToDate:
    @staticmethod
    def convert(value):
        return date.fromisoformat(value)


class NumericToFloat:
    @staticmethod
    def convert(value):
        return float(value)


class NumericToDecimal:
    @staticmethod
    def convert(value):
        return Decimal(value)


POSTGRES_APPSYNC_MAPPER = {
    'jsonb': JsonbToDict,
    'timestamptz': TimestampzToAWSDateTime,
    'timestamp': TimestampzToAWSDateTime,
    'numeric': NumericToFloat
}

POSTGRES_PYTHON_MAPPER = {
    'jsonb': JsonbToDict,
    'timestamptz': TimestampzToDatetimeUTC,
    'timestamp': TimestampzToDatetimeUTC,
    'date': DateToDate,
    'numeric': NumericToDecimal,
}
