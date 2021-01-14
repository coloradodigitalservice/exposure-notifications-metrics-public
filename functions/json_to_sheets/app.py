# /usr/bin/env python3

"""
This script accepts JSON-formatted data (the output of db_to_json.py), and inputs this data to a specified Google Sheets
spreadsheet, taking the newest date since last update.

TODO: Integrate with Kinesis or other data stream to do data diff for us, focus only on updated records

"""


import datetime
import json
import logging
import os.path
import sys
import argparse
from pprint import pformat
from typing import Dict, List, Tuple, cast

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger()
logger.setLevel(level=os.environ.get("LOGLEVEL", "INFO"))


class GoogleSheetsAPIHelper:
    def __init__(self, spreadsheet_id: str = "", sheet_id: str = ""):
        self.credentials = self.init_creds()
        self.service = build(
            "sheets", "v4", credentials=self.credentials, cache_discovery=False)
        self.spreadsheet_id = spreadsheet_id
        self.sheet_id = sheet_id
        self._latest_sheet_row_and_date = None
        self.source_date_format = '%Y-%m-%d %H:%M:%S'
        self.destination_date_format = '%Y-%m-%d %H:%M %p'

    def init_creds(self):
        """
        Initialize credentials, checking for a pickled version
        """
        logger.info("Initializing credentials...")
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets"]
        # See https://developers.google.com/identity/protocols/oauth2/service-account#python
        creds = service_account.Credentials.from_service_account_file(
            "service.json", scopes=scopes
        )
        if not creds.valid:
            logger.info("Credentials invalid - refreshing...")
            creds.refresh(Request())
        logger.debug(
            f"Credentials response: {creds.__dict__} . Is valid?: {creds.valid}")
        return creds

    def read(self, cell_range: str) -> List[List[object]]:
        """
        Read data from the selected sheet at the given range
        :param cell_range: the cell range portion of an A1 notation string,
        e.g for 'Sheet1!A2:E2', "A2:E2"
        """
        range_name = f"{self.sheet_id}!{cell_range}"
        logger.debug(
            f"Reading values for range {range_name}, in spreadsheet {self.spreadsheet_id}")
        result = (
            self.service.spreadsheets().values()
            .get(spreadsheetId=self.spreadsheet_id, range=range_name)
            .execute()
        )
        logger.debug(f"Read result: {result}")
        values = result.get("values", [])
        return values

    def write(self, cell_range: str, values: List[List[str]]):
        """
        Write data to the selected sheet at the given range
        :param cell_range: the cell range portion of an A1 notation string,
        e.g for 'Sheet1!A2:E2', "A2:E2"
        :param values: list of lists of values to insert
        """
        range_name = f"{self.sheet_id}!{cell_range}"
        logger.debug(f"Writing values {values} to range {range_name}...")
        body = {"values": values}
        result = self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id,
                                                             range=range_name,
                                                             valueInputOption="RAW",
                                                             body=body).execute()
        logger.debug(f"Write result: {result}")

    @property
    def latest_sheet_row_and_date(self) -> Tuple[int, datetime.datetime]:
        """
        Returns the latest row and the latest date present at that row
        """
        logger.debug("Getting latest sheet row and date...")
        if not self._latest_sheet_row_and_date:
            all_date_rows = self.read("B:B")
            if len(all_date_rows) == 0:
                self._latest_sheet_row_and_date = latest_date = datetime.datetime(
                    1, 1, 1)
            else:
                latest_date = all_date_rows[-1][0]
                self._latest_sheet_row_and_date = datetime.datetime.strptime(
                    latest_date, self.destination_date_format)
        # Note, while we would ordinarily subtract 1, rows are not 0-indexed, so we can use len here
        latest_row = len(all_date_rows)
        latest_date = self._latest_sheet_row_and_date
        logger.debug(f"Latest row: {latest_row}, latest date: {latest_date}")
        return (latest_row, latest_date)

    def write_encv_values(self, cell_range: str, encv_data: pd.DataFrame):
        """
        Write new values to the sheet, beginning with the newest data
        """
        # Data is retrieved in reverse chronological order
        (latest_sheet_row, latest_sheet_date) = self.latest_sheet_row_and_date

        # We start with the assumption that we should use none of the new data
        first_new_date_index = len(encv_data)
        encv_data["date"] = encv_data["date"].map(
            lambda d: datetime.datetime.strptime(d, self.source_date_format))

        for i, data_point in encv_data.iterrows():
            curr_date = data_point["date"]
            if curr_date > latest_sheet_date:
                logger.debug(f"first new data point: {curr_date}")
                first_new_date_index = i
                break

        remaining_data = encv_data[first_new_date_index:]

        codes_issued_col = "C"
        codes_issued_values = [
            None, None, remaining_data["codes_issued"].tolist(), None, None, None, None]
        codes_claimed_col = "D"
        codes_claimed_values = [None, None, None,
                                remaining_data["codes_claimed"].tolist(), None, None, None]
        date_col = "B"
        date_values = [
            remaining_data["date"].map(lambda d: datetime.datetime.strftime(d, self.destination_date_format)).tolist(
            ), None, None, None, None, None, None
        ]
        '''
        This API expects us to send rows as an array of arrays, one array for each row. If you specify "COLUMNS" for the
        "majorDimension", however, you can instead refer to the values for the specified column instead, which makes it
        easier to do a bulk insert that only touches the specified columns.
        '''
        data = [
            {
                "range": f"{self.sheet_id}!{codes_issued_col}{latest_sheet_row+1}:{codes_issued_col}",
                "values": codes_issued_values,
                "majorDimension": "COLUMNS"
            },
            {
                "range": f"{self.sheet_id}!{codes_claimed_col}{latest_sheet_row+1}:{codes_claimed_col}",
                "values": codes_claimed_values,
                "majorDimension": "COLUMNS"
            },
            {
                "range": f"{self.sheet_id}!{date_col}{latest_sheet_row+1}:{date_col}",
                "values": date_values,
                "majorDimension": "COLUMNS"
            }
        ]
        body = {"valueInputOption": "RAW",
                "data": data}
        logger.debug(f"BODY: {body}")
        response = self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.spreadsheet_id,
                                                                    body=body).execute()
        logger.debug("Cell update response: " + pformat(response))
        num_updated_cells = response.get("totalUpdatedCells")
        logger.info(f"{num_updated_cells} cells updated")
        if len(response.get("responses")) > 0:
            success = True
        else:
            success = False
        return success


def populate_sheet(spreadsheet_id: str, sheet_id: str, data: List[Dict[str, object]]) -> bool:
    """
    Takes input JSON and writes to the specified sheet
    """
    logger.info("Initializing sheet...")
    service = GoogleSheetsAPIHelper(
        spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
    logger.info("Initialized service. Serializing data...")
    df = pd.DataFrame.from_dict(data)
    logger.info("Writing values...")
    success = service.write_encv_values("A:G", df)
    return success


def parse_arguments():
    my_parser = argparse.ArgumentParser()
    my_parser.add_argument('-s',
                           '--sheet',
                           action='store',
                           default="",
                           type=str,
                           dest='spreadsheet_id')
    my_parser.add_argument('-d',
                           '--data',
                           action='store',
                           default=sys.stdin,
                           type=str,
                           dest='data')

    return my_parser.parse_args()


def lambda_handler(event, context):
    logger.info(f"Incoming event: {event}")
    data = event.get("body").get("data")
    success = populate_sheet(
        spreadsheet_id="",
        sheet_id="Source Data",
        data=data
    )
    return {
        "statusCode": 200,
        "body": {
            "success": success
        }
    }

def main():
    sample_data = {"statusCode": 200, "body": {"data": [{"id": 1, "date": "2021-01-22 00:00:00", "codes_claimed": 111, "codes_issued": 222}, {
        "id": 2, "date": "2020-01-23 00:00:00", "codes_claimed": 333, "codes_issued": 444}]}}
    args = parse_arguments()
    logger.info(f"Arguments: {args}")
    args.data = sample_data
    print(lambda_handler(sample_data, None))

if __name__ == "__main__":
    main()
