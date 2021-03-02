import json
import os
import unittest

import boto3
from dotenv import load_dotenv

from data_api_mapper.appsync import AppsyncEvent
from data_api_mapper.data_api import QueryExecutor, ParameterBuilder, GraphQLMapper, DictionaryMapper

load_dotenv()


def read_json_file(path):
    with open(path) as json_file:
        return json.load(json_file)


class TestDataAPI(unittest.TestCase):

    query_executor = None

    @classmethod
    def setUpClass(cls):
        db_name = os.getenv('DB_NAME')
        db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
        secret_arn = os.getenv('SECRET_ARN')
        rds_client = boto3.client('rds-data')
        query_executor = QueryExecutor(rds_client, secret_arn, db_cluster_arn, db_name)
        initial_sql = """
            DROP TABLE IF EXISTS aurora_data_api_test;
            CREATE TABLE aurora_data_api_test (
                id SERIAL,
                a_name TEXT,
                doc JSONB DEFAULT '{}',
                num_numeric NUMERIC (10, 5) DEFAULT 0.0,
                num_float float,
                num_integer integer,
                ts TIMESTAMP WITH TIME ZONE
            );
            INSERT INTO aurora_data_api_test (a_name, doc, num_numeric, num_float, num_integer, ts)
            VALUES ('first row', '{"string_vale": "string1", "int_value": 1, "float_value": 1.11}', 1.12345, 1.11, 1, '1976-11-02 08:45:00 UTC');
            VALUES ('second row', '{"string_vale": "string2", "int_value": 2, "float_value": 2.22}', 2.22, 2.22, 2, '1976-11-02 08:45:00 UTC');
        """
        query_executor.execute(sql=initial_sql, wrap_result=False)
        cls.query_executor = query_executor

    @classmethod
    def tearDownClass(cls):
        cls.query_executor.execute('DROP TABLE IF EXISTS aurora_data_api_test', wrap_result=False)

    def test_types(self):
        parameters = ParameterBuilder().add_long("id", 1).build()
        result = self.query_executor.execute("select * from aurora_data_api_test where id =:id", parameters)
        row = GraphQLMapper(result.metadata).map(result.records)[0]
        self.assertEqual(1, row['id'])
        self.assertEqual('first row', row['a_name'])
        doc = row['doc']
        self.assertEqual('string1', doc['string_vale'])
        self.assertEqual(1, doc['int_value'])
        self.assertEqual(1.11, doc['float_value'])
        self.assertEqual(1.12345, row['num_numeric'])
        self.assertEqual(1.11, row['num_float'])
        self.assertEqual(1, row['num_integer'])


class TestAppSynEvent(unittest.TestCase):
    def test_fields(self):
        event = AppsyncEvent(read_json_file('query.json'))
        self.assertEqual("Hola Mundo", event.name)
        self.assertEqual("holamundo@email.com", event.email)
        self.assertEqual("4169f39a-db3a-4058-a907-3aa6684de0b2", event.username)


if __name__ == '__main__':
    unittest.main()
