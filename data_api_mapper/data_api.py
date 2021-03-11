import json
from dataclasses import dataclass
from typing import List, Dict, Any
from data_api_mapper.converters import GRAPHQL_CONVERTERS


class ParameterBuilder:

    def __init__(self) -> None:
        self.result = []

    @staticmethod
    def build_entry_map(name, value, type, type_hint=None):
        if type_hint:
            return {'name': name, 'value': {type: value}, 'typeHint': type_hint}
        else:
            return {'name': name, 'value': {type: value}}

    def add_null(self, name):
        self.result.append(self.build_entry_map(name, True, 'isNull'))
        return self

    def add_long(self, name, value):
        self.result.append(self.build_entry_map(name, value, 'longValue'))
        return self

    def add_long_or_null(self, name, value):
        if value is not None:
            self.result.append(self.build_entry_map(name, value, 'longValue'))
        else:
            self.add_null(name)
        return self

    def add_string(self, name, value):
        self.result.append(self.build_entry_map(name, value, 'stringValue'))
        return self

    def add_string_or_null(self, name, value):
        if value is not None:
            self.result.append(self.build_entry_map(name, value, 'stringValue'))
        else:
            self.add_null(name)
        return self

    def add_boolean(self, name, value):
        self.result.append(self.build_entry_map(name, value, 'booleanValue'))
        return self

    def add_json(self, name, value):
        self.result.append(self.build_entry_map(name, json.dumps(value), 'stringValue', 'JSON'))
        return self

    def add_json_or_null(self, name, value):
        if value is not None:
            self.result.append(self.build_entry_map(name, json.dumps(value), 'stringValue', 'JSON'))
        else:
            self.add_null(name)
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
        return [x.name if x.table_name == main_table else f'{x.table_name}_{x.name}' for x in self.rows]

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
