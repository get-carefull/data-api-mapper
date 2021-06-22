import ast
import json
import os
import unittest
from datetime import datetime, timezone, date
from decimal import Decimal

import boto3
from dotenv import load_dotenv

from data_api_mapper.appsync import AppsyncEvent, CamelSnakeConverter
from data_api_mapper.converters import TimestampzToDatetimeUTC
from data_api_mapper import DataAPIClient
from data_api_mapper.data_api import ParameterBuilder

load_dotenv()


def read_json_file(path):
    with open(path) as json_file:
        return json.load(json_file)


class TestDataAPI(unittest.TestCase):

    data_client = None

    @classmethod
    def setUpClass(cls):
        db_name = os.getenv('DB_NAME')
        db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
        secret_arn = os.getenv('SECRET_ARN')
        rds_client = boto3.client('rds-data')
        data_client = DataAPIClient(rds_client, secret_arn, db_cluster_arn, db_name)
        initial_sql = """
            DROP TABLE IF EXISTS aurora_data_api_test;
            CREATE TABLE aurora_data_api_test (
                id SERIAL,
                a_name TEXT,
                doc JSONB DEFAULT '{}',
                num_numeric NUMERIC (10, 5) DEFAULT 0.0,
                num_float float,
                num_integer integer,
                ts TIMESTAMP WITH TIME ZONE,
                field_string_null TEXT NULL,
                field_long_null integer NULL,
                field_doc_null JSONB NULL,
                field_boolean BOOLEAN NULL,
                tz_notimezone TIMESTAMP,
                a_date DATE
            );
            INSERT INTO aurora_data_api_test (a_name, doc, num_numeric, num_float, num_integer, ts, tz_notimezone, a_date)
            VALUES ('first row', '{"string_vale": "string1", "int_value": 1, "float_value": 1.11}', 1.12345, 1.11, 1, '1976-11-02 08:45:00 UTC', '2021-03-03 15:51:48.082288', '1976-11-02');
            VALUES ('second row', '{"string_vale": "string2", "int_value": 2, "float_value": 2.22}', 2.22, 2.22, 2, '1976-11-02 08:45:00 UTC', '2021-03-03 15:51:48.082288', '1976-11-02');
        """
        data_client.query(sql=initial_sql)
        cls.data_client = data_client

    def test_datetime(self):
        self.data_client.query('''
            INSERT INTO aurora_data_api_test (id, a_name, doc, num_numeric, num_float, num_integer, ts, tz_notimezone, a_date) 
            VALUES (20, 'first row', '{"string_vale": "string1", "int_value": 1, "float_value": 1.11}', 1.12345, 1.11, 1, '1976-11-02 08:45:00 UTC', '2021-03-03 15:51:48.082456', '1976-11-02');
        ''')
        result = self.data_client.query("select ts, tz_notimezone, a_date from aurora_data_api_test where  id = 20")
        to_test = result[0]
        self.assertEqual(to_test['ts'], datetime.fromisoformat('1976-11-02T08:45:00+00:00'))
        self.assertEqual(to_test['tz_notimezone'], datetime.fromisoformat('2021-03-03T15:51:48.082456+00:00'))
        self.assertEqual(to_test['a_date'], date(1976, 11, 2))

    def test_types(self):
        result = self.data_client.query("select * from aurora_data_api_test where id =:id", {'id': 1})
        row = result[0]
        self.assertEqual(1, row['id'])
        self.assertEqual(datetime.fromisoformat('2021-03-03T15:51:48.082288+00:00'), row['tz_notimezone'])
        self.assertEqual('first row', row['a_name'])
        doc = row['doc']
        self.assertEqual('string1', doc['string_vale'])
        self.assertEqual(1, doc['int_value'])
        self.assertEqual(1.11, doc['float_value'])
        self.assertEqual(Decimal('1.12345'), row['num_numeric'])
        self.assertEqual(1.11, row['num_float'])
        self.assertEqual(1, row['num_integer'])
        self.assertEqual(date(1976, 11, 2), row['a_date'])

    def test_not_table(self):
        result = self.data_client.query("select count(*) from aurora_data_api_test")
        row = result[0]
        self.assertTrue('count' in row)

    def test_data_api_types(self):
        sql = "INSERT INTO aurora_data_api_test (a_name, doc, num_numeric, num_float, num_integer, ts, tz_notimezone, field_string_null, field_boolean, field_long_null, field_doc_null, a_date) values (:name, :doc, :num_numeric, :num_float ,:num_integer, '1976-11-02 08:45:00 UTC', '2021-03-03 15:51:48.082288', :field_string_null, :field_boolean, :field_long_null, :field_doc_null, :a_date) RETURNING id"
        parameters = [
            {'name': 'name', 'value': 'prueba'},
            {'name': 'field_string_null', 'value': None, 'allow_null': True},
            {'name': 'doc', 'value': {'num_int': 1, 'num_float': 45.6, 'somestring': 'hello', 'a_date': date(1976, 11, 2)}},
            {'name': 'num_integer', 'value': 1},
            {'name': 'num_numeric', 'value': Decimal('100.7654')},
            {'name': 'num_float', 'value': 10.123},
            {'name': 'field_boolean', 'value': True},
            {'name': 'field_long_null', 'value': None, 'allow_null': True},
            {'name': 'field_doc_null', 'value': None, 'allow_null': True},
            {'name': 'a_date', 'value': date(1976, 11, 2)}
        ]
        result_map = self.data_client.query(sql, parameters)
        parameters = {"id": result_map[0]['id']}
        result = self.data_client.query("select * from aurora_data_api_test where id = :id", parameters)
        row = result[0]
        self.assertEqual('prueba', row['a_name'])
        self.assertEqual({'num_int': 1, 'num_float': 45.6, 'somestring': 'hello', 'a_date': '1976-11-02'}, row['doc'])
        self.assertEqual(1, row['num_integer'])
        self.assertEqual(10.123, row['num_float'])
        self.assertEqual(Decimal('100.7654'), row['num_numeric'])
        self.assertEqual(True, row['field_boolean'])
        self.assertEqual(None, row['field_string_null'])
        self.assertEqual(None, row['field_long_null'])
        self.assertEqual(None, row['field_doc_null'])
        self.assertEqual(date(1976, 11, 2), row['a_date'])

    def test_hint(self):
        a_json = {'first': 1, 'second': 'string'}
        decimal_str = '10.22332'
        parameters = [{'name': 'a_json', 'value': json.dumps(a_json), 'cast': 'JSON'},
                      {'name': 'a_decimal', 'value': decimal_str, 'cast': 'DECIMAL'}]
        self.data_client.query('''
            INSERT INTO aurora_data_api_test (id, num_numeric, doc) 
            VALUES (101, :a_decimal, :a_json)
        ''', parameters)
        parameters = {"id": 101}
        result = self.data_client.query("select * from aurora_data_api_test where id =:id", parameters)
        row = result[0]
        self.assertEqual(a_json, row['doc'])
        self.assertEqual(Decimal(decimal_str), row['num_numeric'])

    def test_transaction(self):
        transaction = self.data_client.begin_transaction()
        transaction.query('''
            INSERT INTO aurora_data_api_test (id, a_name, doc, num_numeric, num_float, num_integer, ts, tz_notimezone)
            VALUES (345, 'first row', '{"string_vale": "string1", "int_value": 1, "float_value": 1.11}', 1.12345, 1.11, 1, '1976-11-02 08:45:00 UTC', '2021-03-03 15:51:48.082288');
        ''')
        inside_transaction = transaction.query("select * from aurora_data_api_test where id = 345")
        self.assertEqual(1, len(inside_transaction))
        transaction.query('''
            INSERT INTO aurora_data_api_test (id, a_name, doc, num_numeric, num_float, num_integer, ts, tz_notimezone)
            VALUES (346, 'first row', '{"string_vale": "string1", "int_value": 1, "float_value": 1.11}', 1.12345, 1.11, 1, '1976-11-02 08:45:00 UTC', '2021-03-03 15:51:48.082288');
        ''')
        inside_transaction = transaction.query("select * from aurora_data_api_test where id in (345,346)")
        self.assertEqual(2, len(inside_transaction))
        before_commit = self.data_client.query("select * from aurora_data_api_test where id in (345,346)")
        self.assertEqual(0, len(before_commit))
        transaction.commit()
        after_commit = self.data_client.query("select * from aurora_data_api_test where id in (345,346)")
        self.assertEqual(2, len(after_commit))

    def test_transaction_rollback(self):
        transaction = self.data_client.begin_transaction()
        transaction.query('''
            INSERT INTO aurora_data_api_test (id, a_name, doc, num_numeric, num_float, num_integer, ts, tz_notimezone)
            VALUES (355, 'first row', '{"string_vale": "string1", "int_value": 1, "float_value": 1.11}', 1.12345, 1.11, 1, '1976-11-02 08:45:00 UTC', '2021-03-03 15:51:48.082288')
        ''')
        inside_transaction = transaction.query("select * from aurora_data_api_test where id = 355")
        self.assertEqual(1, len(inside_transaction))
        transaction.query('''
            INSERT INTO aurora_data_api_test (id, a_name, doc, num_numeric, num_float, num_integer, ts, tz_notimezone)
            VALUES (356, 'first row', '{"string_vale": "string1", "int_value": 1, "float_value": 1.11}', 1.12345, 1.11, 1, '1976-11-02 08:45:00 UTC', '2021-03-03 15:51:48.082288')
        ''')
        inside_transaction = transaction.query("select * from aurora_data_api_test where id in (355,356)")
        self.assertEqual(2, len(inside_transaction))
        before_rollback = self.data_client.query("select * from aurora_data_api_test where id in (355,356)")
        self.assertEqual(0, len(before_rollback))
        transaction.rollback()
        after_rollback = self.data_client.query("select * from aurora_data_api_test where id in (355,356)")
        self.assertEqual(0, len(after_rollback))

    @classmethod
    def tearDownClass(cls):
        cls.data_client.query('DROP TABLE IF EXISTS aurora_data_api_test')


class TestAppSynEvent(unittest.TestCase):
    def test_fields(self):
        event = AppsyncEvent(read_json_file('query.json'))
        self.assertEqual("Hola Mundo", event.name)
        self.assertEqual("holamundo@email.com", event.email)
        self.assertEqual("4169f39a-db3a-4058-a907-3aa6684de0b2", event.username)


class TestAppSync(unittest.TestCase):
    def test_not_convert_typename(self):
        event = [{'prueba_campo': '2021-03-03 15:51:48.082288', '__typename': 'TYPENAME', 'id_ok': 9771}]
        result = CamelSnakeConverter.dict_to_camel(event)
        self.assertEqual("TYPENAME", result[0]['__typename'])
        self.assertEqual("2021-03-03 15:51:48.082288", result[0]['pruebaCampo'])
        self.assertEqual(9771, result[0]['idOk'])


class TestParameterBuilder(unittest.TestCase):
    def test_parameter_builder(self):
        self.assertEqual('dast', ParameterBuilder().add('string', 'dast').build()[0]['value']['stringValue'])
        self.assertEqual(1, ParameterBuilder().add('long', 1).build()[0]['value']['longValue'])
        self.assertEqual(1.123, ParameterBuilder().add('double', 1.123).build()[0]['value']['doubleValue'])
        self.assertEqual(False, ParameterBuilder().add('boolean', False).build()[0]['value']['booleanValue'])
        parameter_json = ParameterBuilder().add('json', {'key':'as'}).build()[0]
        self.assertEqual('JSON', parameter_json['typeHint'])
        self.assertEqual({'key':'as'}, ast.literal_eval(parameter_json['value']['stringValue']))
        parameter_json_list = ParameterBuilder().add('json', ['MANAGER', 'PRUEBA']).build()[0]
        self.assertEqual('JSON', parameter_json_list['typeHint'])
        self.assertEqual(['MANAGER', 'PRUEBA'], ast.literal_eval(parameter_json_list['value']['stringValue']))
        date_object = ParameterBuilder().add('date', datetime(2017, 6, 11, 10, 20, 30).date()).build()[0]
        self.assertEqual('DATE', date_object['typeHint'])
        self.assertEqual('2017-06-11', date_object['value']['stringValue'])
        datetime_object = ParameterBuilder().add('datetime', datetime(2017, 6, 11, 10, 20, 30, 100)).build()[0]
        self.assertEqual('TIMESTAMP', datetime_object['typeHint'])
        self.assertEqual('2017-06-11 10:20:30.000100', datetime_object['value']['stringValue'])
        decimal = ParameterBuilder().add('decimal', Decimal(1.123412123123213035569278872571885585784912109375)).build()[0]
        self.assertEqual('DECIMAL', decimal['typeHint'])
        self.assertEqual('1.123412123123213035569278872571885585784912109375', decimal['value']['stringValue'])

    def test_parameter_builder_with_exception_by_none(self):
        with self.assertRaises(Exception) as context:
            ParameterBuilder().add('string', None).build()[0]['value']['stringValue']

        self.assertEqual('The data type of the value does not match against any of the expected', str(context.exception))

    def test_parameter_builder_with_null(self):
        self.assertEqual('dast', ParameterBuilder().add('string', 'dast').build()[0]['value']['stringValue'])
        self.assertEqual(1, ParameterBuilder().add('long', 1).build()[0]['value']['longValue'])
        self.assertEqual(1.123, ParameterBuilder().add('double', 1.123).build()[0]['value']['doubleValue'])
        self.assertEqual(False, ParameterBuilder().add('boolean', False).build()[0]['value']['booleanValue'])
        parameter_json = ParameterBuilder().add('json', {'key':'as'}).build()[0]
        self.assertEqual('JSON', parameter_json['typeHint'])
        self.assertEqual({'key':'as'}, ast.literal_eval(parameter_json['value']['stringValue']))
        date_object = ParameterBuilder().add('date', datetime(2017, 6, 11, 10, 20, 30).date()).build()[0]
        self.assertEqual('DATE', date_object['typeHint'])
        self.assertEqual('2017-06-11', date_object['value']['stringValue'])
        datetime_object = ParameterBuilder().add('datetime', datetime(2017, 6, 11, 10, 20, 30)).build()[0]
        self.assertEqual('TIMESTAMP', datetime_object['typeHint'])
        self.assertEqual('2017-06-11 10:20:30', datetime_object['value']['stringValue'])
        decimal = ParameterBuilder().add('decimal', Decimal(1.123412123123213035569278872571885585784912109375)).build()[0]
        self.assertEqual('DECIMAL', decimal['typeHint'])
        self.assertEqual('1.123412123123213035569278872571885585784912109375', decimal['value']['stringValue'])
        self.assertEqual(True, ParameterBuilder().add('string', None).build()[0]['value']['isNull'])

    def test_add_dictionary(self):
        a_dict = {
            'a_string': 'hello',
            'an_int': 4
        }
        params = ParameterBuilder().add_dictionary(a_dict).build()
        self.assertEqual('a_string', params[0]['name'])
        self.assertEqual('hello', params[0]['value']['stringValue'])
        self.assertEqual('an_int', params[1]['name'])
        self.assertEqual(4, params[1]['value']['longValue'])


class TimestampzToDatetimeUTCTest(unittest.TestCase):

    converter = TimestampzToDatetimeUTC()

    def test_converter_missing_millis(self):
        result = self.converter.convert('2021-03-22 23:52:48.650')
        expected = datetime(2021, 3, 22, 23, 52, 48, 650000, tzinfo=timezone.utc)
        self.assertEqual(expected, result)

    def test_converter_missing_millis2(self):
        result = self.converter.convert('2020-10-18 16:25:46.029')
        expected = datetime(2020, 10, 18, 16, 25, 46, 29000, tzinfo=timezone.utc)
        self.assertEqual(expected, result)

    def test_converter_no_millis(self):
        result = self.converter.convert('2020-10-18 16:25:46')
        expected = datetime(2020, 10, 18, 16, 25, 46, 0, tzinfo=timezone.utc)
        self.assertEqual(expected, result)

if __name__ == '__main__':
    unittest.main()
