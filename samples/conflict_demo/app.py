"""Synthetic scanner fixture; not a real package migration recommendation."""
from dateutil.parser import parse


def parse_date(value):
    return parse(value)
