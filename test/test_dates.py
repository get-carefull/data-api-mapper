import os
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import boto3
from dotenv import load_dotenv

from data_api_mapper import DataAPIClient
from data_api_mapper.utils import DatetimeUtils

load_dotenv()


class TestDatetimeOffset(unittest.TestCase):

    data_client = None

    @classmethod
    def setUpClass(cls):
        db_name = os.getenv('DB_NAME')
        db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
        secret_arn = os.getenv('SECRET_ARN')
        rds_client = boto3.client('rds-data')
        data_client = DataAPIClient(rds_client, secret_arn, db_cluster_arn, db_name)
        cls.data_client = data_client
        initial_sql = """
            DROP TABLE IF EXISTS aurora_data_api_dates_test;
            CREATE TABLE aurora_data_api_dates_test (id INTEGER, datetime timestamp with time zone, datetime_offset numeric);
        """
        data_client.query(sql=initial_sql)

    def test_naive(self):
        dt1 = datetime(2022, 4, 1, 16, 30, 3)
        params = {'id': 1, 'datetime': dt1}
        self.data_client.query('insert into aurora_data_api_dates_test (id, datetime) values (:id, :datetime)', params)
        dt2 = self.data_client.query('select datetime from aurora_data_api_dates_test where id = 1')[0]['datetime']
        self.assertEqual(dt1, dt2.replace(tzinfo=None))

    def test_utc(self):
        dt1 = datetime(2022, 4, 1, 16, 30, 3, tzinfo=timezone.utc)
        params = {'id': 2, 'datetime': dt1}
        self.data_client.query('insert into aurora_data_api_dates_test (id, datetime) values (:id, :datetime)', params)
        dt2 = self.data_client.query('select datetime from aurora_data_api_dates_test where id = 2')[0]['datetime']
        self.assertEqual(dt1, dt2)

    def test_los_angeles(self):
        info = ZoneInfo("America/Los_Angeles")
        d_los_angeles = datetime(2022, 4, 1, 16, 30, 3, tzinfo=info)
        dt, offset = DatetimeUtils.to_utc_and_offset(d_los_angeles)
        params = {'id': 3, 'datetime': dt, 'datetime_offset': offset}
        sql = '''
            insert into aurora_data_api_dates_test (id, datetime, datetime_offset) 
            values (:id, :datetime, :datetime_offset)
        '''
        self.data_client.query(sql, params)
        d = self.data_client.query('select datetime, datetime_offset from aurora_data_api_dates_test where id = 3')[0]
        self.assertEqual(d['datetime'], d_los_angeles.astimezone(timezone.utc))
        self.assertEqual(d['datetime_offset'], -7)



    @classmethod
    def tearDownClass(cls):
        cls.data_client.query('DROP TABLE IF EXISTS aurora_data_api_dates_test')
