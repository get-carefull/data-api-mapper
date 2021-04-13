import json
from datetime import datetime, timezone


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


class NumericToFloat:
    @staticmethod
    def convert(value):
        return float(value)


GRAPHQL_CONVERTERS = {
    'jsonb': JsonbToDict,
    'timestamptz': TimestampzToAWSDateTime,
    'timestamp': TimestampzToAWSDateTime,
    'numeric': NumericToFloat
}
