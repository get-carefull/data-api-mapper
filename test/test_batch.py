import os
import unittest

import boto3
from dotenv import load_dotenv

from data_api_mapper import DataAPIClient

load_dotenv()


class TestPagination(unittest.TestCase):

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
            DROP TABLE IF EXISTS aurora_data_api_batch_test;
            CREATE TABLE aurora_data_api_batch_test ( id INTEGER, id_text VARCHAR);
        """
        data_client.query(sql=initial_sql)

    def test_batch(self):
        sql = ''' 
                insert into aurora_data_api_batch_test (id, id_text) values (:id, :id_text)
            '''
        parameters = [{'id': x, 'id_text': str(x)} for x in range(1, 101)]
        self.data_client.batch_query(sql, parameters)
        count = self.data_client.query('select count(*) from aurora_data_api_batch_test')[0]['count']
        self.assertEqual(100, count)
        self.data_client.query('delete from aurora_data_api_batch_test')

    def test_batch_tx(self):
        sql = ''' 
                insert into aurora_data_api_batch_test (id, id_text) values (:id, :id_text)
            '''
        parameters = [{'id': x, 'id_text': str(x)} for x in range(1, 101)]
        tx = self.data_client.begin_transaction()
        tx.data_client.batch_query(sql, parameters)
        parameters = [{'id': x, 'id_text': str(x)} for x in range(101, 201)]
        tx.data_client.batch_query(sql, parameters)
        tx.commit()
        count = self.data_client.query('select count(*) from aurora_data_api_batch_test')[0]['count']
        self.assertEqual(200, count)
        self.data_client.query('delete from aurora_data_api_batch_test')

    @classmethod
    def tearDownClass(cls):
        cls.data_client.query('DROP TABLE IF EXISTS aurora_data_api_batch_test')
