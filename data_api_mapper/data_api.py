from dataclasses import dataclass
from typing import List, Dict, Any
from data_api_mapper.converters import GRAPHQL_CONVERTERS


class ParameterBuilder:

    def __init__(self) -> None:
        self.result = []

    @staticmethod
    def build_entry_map(name, value, type):
        return {'name': name, 'value': {type: value}}

    def add_long(self, name, value):
        self.result.append(self.build_entry_map(name, value, 'longValue'))
        return self

    def add_string(self, name, value):
        self.result.append(self.build_entry_map(name, value, 'stringValue'))
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


class QueryExecutor:

    def __init__(self, rds_client, secret_arn, cluster_arn, database_name) -> None:
        super().__init__()
        self.rds_client = rds_client
        self.secret_arn = secret_arn
        self.cluster_arn = cluster_arn
        self.database_name = database_name

    def execute(self, sql, parameters) -> QueryResponse:
        response = self.rds_client.execute_statement(
            secretArn=self.secret_arn, database=self.database_name,
            resourceArn=self.cluster_arn, includeResultMetadata=True,
            sql=sql, parameters=parameters
        )
        return QueryResponse.from_dict(response)


class DictionaryMapper:

    def __init__(self, metadata: QueryMetadata, converter_map=None):
        self.fields = metadata.field_names()
        self.converters = metadata.converters(converter_map)

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
