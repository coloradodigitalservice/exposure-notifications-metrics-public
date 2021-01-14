# /usr/bin/env python

import datetime
import os

import app as json_to_sheets
import pandas as pd
import pytest

from tests.settings import settings
from tests.utils import GoogleDriveAPIHelper, translate_date_string


@pytest.fixture
def sheets_api():
    helper = json_to_sheets.GoogleSheetsAPIHelper()
    yield helper


@pytest.fixture
def drive_api():
    helper = GoogleDriveAPIHelper()
    yield helper
    helper.cleanup()


@pytest.fixture
def header():
    return ["Row ID", "UTC", "# Codes Issued", "# Codes Claimed",
            "# iOS activations (approximate)", "# Android downloads", "# Android Uninstalls"]


def test_write(sheets_api, drive_api, header):
    file_id = drive_api.create_spreadsheet(
        title="Test Sheet", extra_user=settings.extra_user)
    sheets_api.spreadsheet_id = file_id
    sheets_api.sheet_id = "Sheet1"
    values = [
        header,
        ["ai2o3jr1", "2020-10-25 6:00 AM", "890", "320", "678", "789", "57"]
    ]
    sheets_api.write("A:G", values)
    assert values == sheets_api.read("A:G")


def test_latest_sheet_row_and_date(sheets_api, drive_api, header):
    file_id = drive_api.create_spreadsheet(
        title="Test Sheet", extra_user=settings.extra_user)
    sheets_api.spreadsheet_id = file_id
    sheets_api.sheet_id = "Sheet1"
    values = [
        header,
        ["1", "2020-01-01 6:00 AM", "890", "320", "678", "789", "57"],
        ["2", "2020-02-01 6:00 AM", "890", "320", "678", "789", "57"],
        ["3", "2020-03-01 6:00 AM", "890", "320", "678", "789", "57"],
        ["4", "2020-04-01 6:00 AM", "890", "320", "678", "789", "57"],
        ["5", "2020-05-01 6:00 AM", "890", "320", "678", "789", "57"],
        ["6", "2020-06-01 6:00 AM", "890", "320", "678", "789", "57"]
    ]
    sheets_api.write("A:G", values)
    (latest_sheet_row, latest_sheet_date) = sheets_api.latest_sheet_row_and_date
    assert latest_sheet_row == 7
    assert latest_sheet_date == datetime.datetime(2020, 6, 1, 6, 0)


def test_populate_sheet(drive_api, sheets_api, header):
    data = [
        {"id": '31', "date": "2020-12-22 00:00:00",
            "codes_issued": '222', "codes_claimed": '111'},
        {"id": '30', "date": "2020-12-23 00:00:00",
            "codes_issued": '444', "codes_claimed": '333'},
        {"id": '29', "date": "2020-12-24 00:00:00",
            "codes_issued": '666', "codes_claimed": '555'},
        {"id": '28', "date": "2020-12-25 00:00:00",
            "codes_issued": '888', "codes_claimed": '777'}
    ]
    file_id = drive_api.create_spreadsheet(
        title="Test Sheet", extra_user=settings.extra_user)
    sheets_api.spreadsheet_id = file_id
    sheets_api.sheet_id = "Sheet1"

    json_to_sheets.populate_sheet(
        spreadsheet_id=file_id, sheet_id="Sheet1", data=data)
    df = pd.DataFrame.from_dict(data)
    df['id'] = ''  # we don't write the ids
    # We still need to convert between date formats
    df["date"] = df["date"].map(lambda d: translate_date_string(sheets_api, d))

    values_sheets_format = df.values.tolist()
    assert values_sheets_format == sheets_api.read("A:G")
