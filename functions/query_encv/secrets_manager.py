import base64
import json
import logging

import boto3
from botocore.exceptions import ClientError


class SecretsManager:
    def __init__(self):
        session = boto3.session.Session()
        self.client = session.client(
            service_name='secretsmanager',
            region_name=session.region_name
        )

    def get(self, secret_name: str, secret_key: str = None):
        result = None
        try:
            get_secret_value_response = self.client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            logging.error(
                f"Encountered error in fetching secret {secret_name}: {e}")
            raise e
        else:
            # Decrypts secret using the associated KMS CMK.
            # Depending on whether the secret is a string or binary, one of these fields will be populated.
            if 'SecretString' in get_secret_value_response:
                secret = get_secret_value_response['SecretString']
                json_secret = json.loads(secret)
                if secret_key:
                    return json_secret[secret_key]
                else:
                    return json_secret
            else:
                decoded_binary_secret = base64.b64decode(
                    get_secret_value_response['SecretBinary'])
                result = decoded_binary_secret.password
        return result
