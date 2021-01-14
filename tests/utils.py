# /usr/bin/env python3

import datetime
import logging
import os
import pickle
from pprint import pformat

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


class GoogleDriveAPIHelper:
    def __init__(self, spreadsheet_id: str = "", sheet_id: str = ""):
        self.credentials = self.init_creds()
        self.service = build(
            "drive", "v3", credentials=self.credentials, cache_discovery=False)
        self.created_files = []

    def init_creds(self):
        """
        Initialize credentials, checking for a pickled version
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                scopes = ["https://www.googleapis.com/auth/drive"]
                creds = service_account.Credentials.from_service_account_file(
                    "service.json", scopes=scopes
                )
            # Save the credentials for the next run
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)
        return creds

    def create_spreadsheet(self, title: str, extra_user: str):
        """
        Create a spreadsheet and share it with a given user to inspect contents
        """
        data = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        sheet_response = self.service.files().create(body=data).execute()
        logging.debug("Sheet Response: " + pformat(sheet_response))
        file_id = sheet_response.get("id")
        if extra_user:
            self.grant_permissions(
                spreadsheet_id=file_id, extra_user=extra_user)
        self.created_files.append(file_id)
        return file_id

    def grant_permissions(self, spreadsheet_id: str, extra_user: str):
        """
        By default, spreadsheets created by service accounts are not visible to other users.
        You can add an "extra_user" property in your .env file / environment to have this user added to your sheet
        so you can check up on progress.
        """
        permissions = {
            "role": "writer",
            "type": "user",
            "emailAddress": extra_user
        }

        permissions_response = self.service.permissions().create(
            fileId=spreadsheet_id, body=permissions).execute()
        logging.debug("Permissions Response: " + pformat(permissions_response))

    def cleanup(self):
        logging.debug(f"Cleaning up...")
        for file_id in self.created_files:
            logging.debug(f"Removing file: {file_id}")
            self.service.files().delete(fileId=file_id).execute()


def translate_date_string(helper: GoogleDriveAPIHelper, date_string: str) -> str:
    parsed_date = datetime.datetime.strptime(
        date_string, helper.source_date_format)
    translated_date_string = datetime.datetime.strftime(
        parsed_date, helper.destination_date_format)
    return translated_date_string
