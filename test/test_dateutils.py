import unittest
from datetime import datetime, timezone
from data_api_mapper.utils import DatetimeUtils
from zoneinfo import ZoneInfo


class TestDatetimeOffset(unittest.TestCase):

    def test_naive(self):
        dt1 = datetime(2022, 4, 1, 16, 30, 3)
        dt2, offset = DatetimeUtils.to_utc_and_offset(dt1)
        self.assertEqual(offset, None)
        self.assertEqual(dt2, dt1.replace(tzinfo=timezone.utc))

    def test_utc(self):
        dt1 = datetime(2022, 4, 1, 16, 30, 3, tzinfo=timezone.utc)
        dt2, offset = DatetimeUtils.to_utc_and_offset(dt1)
        self.assertEqual(offset, None)
        self.assertEqual(dt2, dt1)

    def test_utc(self):
        dt1 = datetime(2022, 4, 1, 16, 30, 3, tzinfo=ZoneInfo("America/Los_Angeles"))
        dt2, offset = DatetimeUtils.to_utc_and_offset(dt1)
        self.assertEqual(offset, -7 * 3600)
        self.assertEqual(dt2, dt1.astimezone(timezone.utc))

