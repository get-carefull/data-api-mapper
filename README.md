# Data API Mapper
The **Data API Mapper** is a lightweight wrapper for Amazon Aurora Serverless Data API. It's STRONGLY inspired by [DataApiClient](https://github.com/jeremydaly/data-api-client).
Currently, it only maps PostgreSQL types, but it can be easily extended to add MySQL.

## Motivation
Check https://github.com/jeremydaly/data-api-client#why-do-i-need-this

## How to use this module

```python
import os
import boto3
from data_api_mapper import DataAPIClient

db_name = os.getenv('DB_NAME')
db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
secret_arn = os.getenv('SECRET_ARN')

rds_client = boto3.client('rds-data')
data_client = DataAPIClient(rds_client, secret_arn, db_cluster_arn, db_name)
```

## Running a query
Once initialized, running a query is super simple. Use the `query()` method and pass in your SQL statement:

```python
result = data_client.query('SELECT * FROM myTable')
```

By default, this will return your rows as an array of dictionaries with column names as key names and the values as values, converted to python types:
For example, for this database:
```sql
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
```
this query 
```pyton 
self.data_client.query("select * from aurora_data_api_test where id (1,2)"
```
will return:
```python
[{'id': 1, 'a_name': 'first row', 'doc': {'int_value': 1, 'float_value': 1.11, 'string_vale': 'string1'}, 'num_numeric': Decimal('1.12345'), 'num_float': 1.11, 'num_integer': 1, 'ts': datetime.datetime(1976, 11, 2, 8, 45, tzinfo=datetime.timezone.utc), 'field_string_null': None, 'field_long_null': None, 'field_doc_null': None, 'field_boolean': None, 'tz_notimezone': datetime.datetime(2021, 3, 3, 15, 51, 48, 82288, tzinfo=datetime.timezone.utc), 'a_date': datetime.date(1976, 11, 2)}, 
 {'id': 2, 'a_name': 'prueba', 'doc': {'a_date': '1976-11-02', 'num_int': 1, 'num_float': 45.6, 'somestring': 'hello'}, 'num_numeric': Decimal('100.76540'), 'num_float': 10.123, 'num_integer': 1, 'ts': datetime.datetime(1976, 11, 2, 8, 45, tzinfo=datetime.timezone.utc), 'field_string_null': None, 'field_long_null': None, 'field_doc_null': None, 'field_boolean': True, 'tz_notimezone': datetime.datetime(2021, 3, 3, 15, 51, 48, 82288, tzinfo=datetime.timezone.utc), 'a_date': datetime.date(1976, 11, 2)}]
```


By default, `query()` receives a dictionary that maps PostgreSQL types to python types.
```python
POSTGRES_PYTHON_MAPPER = {
    'jsonb': JsonbToDict,
    'timestamptz': TimestampzToDatetimeUTC,
    'timestamp': TimestampzToDatetimeUTC,
    'date': DateToDate,
    'numeric': NumericToDecimal,
}

class DataAPIClient:

    def __init__(self, rds_client, secret_arn, cluster_arn, database_name) -> None:
        ...
    def query(self, sql, parameters=None, mapper=POSTGRES_PYTHON_MAPPER):
        ...

```

There is also a mapper for AppSync, you can check the mappers [here](https://github.com/get-carefull/data-api-mapper/blob/master/data_api_mapper/converters.py).
<br>
If you use MySQL you need a mapper.



## Running a query with parameters

To query with parameters, you can use named parameters in your SQL, and then provide an object containing your parameters as the second argument to the `query()` method and the client does the conversion for you:

```python
import datetime
result = data_client.query(
    'SELECT * FROM myTable WHERE id = :id AND created > :createDate',
    { 'id': 2, 'createDate': datetime.date(2021,6,1) }
)
```
For all the conversions, check [here](https://github.com/get-carefull/data-api-mapper/blob/master/data_api_mapper/data_api.py#L10) 

## Transactions

```python 
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
```






