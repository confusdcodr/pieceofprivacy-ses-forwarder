import uuid

import boto3
import pytest
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from ses_forwarder.ses_forwarder.utils import LookupKey


def test_add_destination(lookup_email):
    """
    Ensure you can add a destination to the table
    """
    hash_value = "test_add_destination#pieceofprivacy.com"
    range_value = "test_add_destination@pieceofprivacy.com"

    item = {
        LookupKey.HASH_KEY.value: hash_value,
        LookupKey.RANGE_KEY.value: range_value,
    }

    response = lookup_email.add_destination(item)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_lookup_destination(ddb_resource, lookup_email):
    hash_value = "test_lookup_destination#pieceofprivacy.com"
    range_value = "test_lookup_destination@pieceofprivacy.com"

    item = {
        LookupKey.HASH_KEY.value: hash_value,
        LookupKey.RANGE_KEY.value: range_value,
    }

    lookup_email.add_destination(item)

    response = lookup_email.lookup_destination(hash_value)
    assert response[0] == item
