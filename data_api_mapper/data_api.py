import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import reduce
from typing import List, Dict, Any
from data_api_mapper.converters import POSTGRES_PYTHON_MAPPER


class ParameterBuilder:

    def __init__(self) -> None:
        self.result = []

    @staticmethod
    def build_entry_map(name, value, type, type_hint=None):
        if type_hint is not None:
            return {'name': name, 'value': {type: value}, 'typeHint': type_hint}
        else:
            return {'name': name, 'value': {type: value}}

    @staticmethod
    def json_serial(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    def add(self, name, value):
        if isinstance(value, str):
            self.result.append(self.build_entry_map(name, value, 'stringValue'))
            return self
        elif isinstance(value, bool):
            self.result.append(self.build_entry_map(name, value, 'booleanValue'))
            return self
        elif isinstance(value, int):
            self.result.append(self.build_entry_map(name, value, 'longValue'))
            return self
        elif isinstance(value, dict):
            self.result.append(self.build_entry_map(name, json.dumps(value, default=self.json_serial), 'stringValue', 'JSON'))
            return self
        elif isinstance(value, list):
            self.result.append(self.build_entry_map(name, json.dumps(value, default=self.json_serial), 'stringValue', 'JSON'))
            return self
        elif isinstance(value, float):
            self.result.append(self.build_entry_map(name, value, 'doubleValue'))
            return self
        elif isinstance(value, datetime):
            self.result.append(self.build_entry_map(name, str(value), 'stringValue', 'TIMESTAMP'))
            return self
        elif isinstance(value, date):
            self.result.append(self.build_entry_map(name, str(value), 'stringValue', 'DATE'))
            return self
        elif isinstance(value, Decimal):
            self.result.append(self.build_entry_map(name, str(value), 'stringValue', 'DECIMAL'))
            return self
        elif value is None:
            self.result.append(self.build_entry_map(name, True, 'isNull'))
            return self
        else:
            raise ValueError('The data type of the value does not match against any of the expected')

    def add_dictionary(self, a_dict):
        for x in a_dict.keys():
            self.add(x, a_dict[x])
        return self

    def build(self):
        return self.result

    def from_query(self, parameters) -> List:
        if not parameters:
            return []
        if isinstance(parameters, list):
            for param in parameters:
                name = param['name']
                value = param['value']
                if 'cast' in param:
                    self.result.append({'name': name, 'value': {'stringValue': value}, 'typeHint': param['cast']})
                else:
                    self.add(name, value)
        elif isinstance(parameters, dict):
            self.add_dictionary(parameters)
        return self.build()


@dataclass
class RowMetadata:
    name: str
    table_name: str
    type_name: str
    nullable: bool

    @staticmethod
    def from_dict(a_dict):
        return RowMetadata(a_dict['name'], a_dict['tableName'], a_dict['typeName'], a_dict['nullable'] != 0)


@dataclass
class QueryMetadata:
    rows: List[RowMetadata]

    def field_names(self):
        return [x.name for x in self.rows]

    def converters(self, converter_map) -> List:
        return [converter_map.get(x.type_name, None) for x in self.rows]


@dataclass
class QueryResponse:
    records: List[List[Dict[str, Any]]]
    metadata: QueryMetadata

    @staticmethod
    def from_dict(a_dict):
        row_metadata_list = [RowMetadata.from_dict(x) for x in a_dict['columnMetadata']]
        return QueryResponse(a_dict['records'], QueryMetadata(row_metadata_list))


class Transaction:
    def __init__(self, data_client) -> None:
        super().__init__()
        self.rds_client = data_client.rds_client
        self.secret_arn = data_client.secret_arn
        self.cluster_arn = data_client.cluster_arn
        self.database_name = data_client.database_name
        self.data_client = data_client
        transaction = self.rds_client.begin_transaction(
            secretArn=self.secret_arn, database=self.database_name, resourceArn=self.cluster_arn
        )
        self.transaction_id = transaction['transactionId']

    def query(self, sql, parameters=(), mapper=POSTGRES_PYTHON_MAPPER) -> Dict[str, Any]:
        return self.data_client.query(sql, parameters, mapper, self.transaction_id)

    def commit(self) -> Dict[str, str]:
        return self.rds_client.commit_transaction(
            secretArn=self.secret_arn, resourceArn=self.cluster_arn, transactionId=self.transaction_id
        )

    def rollback(self) -> Dict[str, str]:
        return self.rds_client.rollback_transaction(
            secretArn=self.secret_arn, resourceArn=self.cluster_arn, transactionId=self.transaction_id
        )


class DataAPIClient:

    def __init__(self, rds_client, secret_arn, cluster_arn, database_name, mapper=POSTGRES_PYTHON_MAPPER) -> None:
        super().__init__()
        self.rds_client = rds_client
        self.secret_arn = secret_arn
        self.cluster_arn = cluster_arn
        self.database_name = database_name
        self.mapper = mapper

    def query(self, sql, parameters=None, mapper=None, transaction_id=None):
        this_mapper = mapper if mapper is not None else self.mapper
        data_client_params = ParameterBuilder().from_query(parameters)
        config = {
            'secretArn': self.secret_arn, 'database': self.database_name,
            'resourceArn': self.cluster_arn, 'includeResultMetadata': True,
            'sql': sql, 'parameters': data_client_params
        }
        if transaction_id is not None:
            config['transactionId'] = transaction_id
        response = self.rds_client.execute_statement(**config)
        if 'columnMetadata' in response:
            response = QueryResponse.from_dict(response)
            return DictionaryMapper(response.metadata, this_mapper).map(response.records)
        else:
            return response['numberOfRecordsUpdated']

    def query_paginated(self, sql, parameters=None, mapper=POSTGRES_PYTHON_MAPPER, page_size=100):
        paginator = self.paginator(sql, parameters, mapper, page_size)
        return reduce(lambda x, y: x+y, paginator)

    def paginator(self, sql, parameters=None, mapper=POSTGRES_PYTHON_MAPPER, page_size=100):
        offset = 0

        def paginate():
            nonlocal offset
            while True:
                sql_paginated = f'{sql} limit {page_size} offset {offset}'
                response = self.query(sql_paginated, parameters, mapper)
                yield response
                if len(response) < page_size:
                    return
                else:
                    offset += page_size

        return paginate()

    def begin_transaction(self):
        return Transaction(self)


class DictionaryMapper:

    def __init__(self, metadata: QueryMetadata, converter_map=None):
        self.fields = metadata.field_names()
        self.converters = metadata.converters(converter_map) if converter_map else [None for _ in range(0, len(self.fields))]

    @staticmethod
    def map_field(field_data, converter):
        key, value = list(field_data.items())[0]
        return None if key == 'isNull' else value if converter is None else converter.convert(value)

    def map_record(self, record):
        return {self.fields[i]: self.map_field(record[i], self.converters[i]) for i in range(0, len(record))}

    def map(self, records):
        return [self.map_record(x) for x in records]
