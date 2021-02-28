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
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


GRAPHQL_CONVERTERS = {
    'jsonb': JsonbToDict,
    'timestamptz': TimestampzToAWSDateTime
}
