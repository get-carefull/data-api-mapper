from datetime import timezone, timedelta


class DatetimeUtils:

    @staticmethod
    def is_aware(d):
        return d.tzinfo is not None and d.tzinfo.utcoffset(d) is not None

    @staticmethod
    def is_naive(d):
        return not DatetimeUtils.is_aware(d)

    @staticmethod
    def to_utc_and_offset(d):
        if DatetimeUtils.is_naive(d):
            return d.replace(tzinfo=timezone.utc), None
        offset = int(d.utcoffset() / timedelta(hours=1))
        offset = offset if offset != 0 else None
        return d.astimezone(timezone.utc), offset




