import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any
from data_api_mapper.converters import GRAPHQL_CONVERTERS


class ParameterBuilder:

    def __init__(self) -> None:
        self.result = []

    @staticmethod
    def build_entry_map(name, value, type, type_hint=None):
        if type_hint is not None:
            return {'name': name, 'value': {type: value}, 'typeHint': type_hint}
        else:
            return {'name': name, 'value': {type: value}}

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
            self.result.append(self.build_entry_map(name, json.dumps(value), 'stringValue', 'JSON'))
            return self
        elif isinstance(value, list):
            self.result.append(self.build_entry_map(name, json.dumps(value), 'stringValue', 'JSON'))
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
        else:
            raise ValueError('The data type of the value does not match against any of the expected')

    def add_or_null(self, name, value):
        if value is None:
            self.result.append(self.build_entry_map(name, True, 'isNull'))
            return self
        else:
            self.add(name, value)
            return self

    def add_dictionary(self, a_dict):
        for x in a_dict.keys():
            self.add(x, a_dict[x])
        return self

    def build(self):
        return self.result


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

    @property
    def main_table(self):
        names = [x.table_name for x in self.rows]
        return max(names, key=names.count)

    def field_names(self):
        main_table = self.main_table
        return [x.name if x.table_name == main_table or not x.table_name
                else f'{x.table_name}_{x.name}'
                for x in self.rows]

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
    def __init__(self, rds_client, secret_arn, cluster_arn, database_name) -> None:
        super().__init__()
        self.rds_client = rds_client
        self.secret_arn = secret_arn
        self.cluster_arn = cluster_arn
        self.database_name = database_name
        transaction = rds_client.begin_transaction(
            secretArn=self.secret_arn, database=self.database_name, resourceArn=self.cluster_arn
        )
        self.transaction_id = transaction['transactionId']

    def execute(self, sql, parameters=()) -> Dict[str, Any]:
        return self.rds_client.execute_statement(
            secretArn=self.secret_arn, database=self.database_name,
            resourceArn=self.cluster_arn, includeResultMetadata=True,
            sql=sql, parameters=parameters, transactionId=self.transaction_id
        )

    def commit(self) -> Dict[str, str]:
        return self.rds_client.commit_transaction(
            secretArn=self.secret_arn, resourceArn=self.cluster_arn, transactionId=self.transaction_id
        )

    def rollback(self) -> Dict[str, str]:
        return self.rds_client.rollback_transaction(
            secretArn=self.secret_arn, resourceArn=self.cluster_arn, transactionId=self.transaction_id
        )


class DataAPIClient:

    def __init__(self, rds_client, secret_arn, cluster_arn, database_name) -> None:
        super().__init__()
        self.rds_client = rds_client
        self.secret_arn = secret_arn
        self.cluster_arn = cluster_arn
        self.database_name = database_name

    def execute(self, sql, parameters=(), wrap_result=True) -> QueryResponse:
        response = self.rds_client.execute_statement(
            secretArn=self.secret_arn, database=self.database_name,
            resourceArn=self.cluster_arn, includeResultMetadata=True,
            sql=sql, parameters=parameters
        )
        return QueryResponse.from_dict(response) if wrap_result else response

    def execute_paginated(self, sql, parameters=(), page_size=100):
        return self.paginate(QueryResponse([], None), sql, parameters, page_size, 0)

    def paginate(self, result: QueryResponse, sql, parameters, page_size, offset):
        sql_paginated = f'{sql} limit {page_size} offset {offset}'
        response = self.execute(sql_paginated, parameters)
        result.records.extend(response.records)
        result.metadata = response.metadata
        if len(response.records) < page_size:
            return result
        else:
            return self.paginate(result, sql, parameters, page_size, offset + page_size)


    def begin_transaction(self):
        return Transaction(self.rds_client, self.secret_arn, self.cluster_arn, self.database_name)


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


class GraphQLMapper(DictionaryMapper):

    def __init__(self, metadata: QueryMetadata):
        super().__init__(metadata, GRAPHQL_CONVERTERS)
