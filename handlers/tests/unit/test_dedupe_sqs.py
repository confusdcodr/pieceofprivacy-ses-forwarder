import uuid

import boto3
import pytest
from botocore.exceptions import ClientError


def test_create_item(dedupe_sqs):
    """
    Ensure that you can create the initial dedupe item
    """
    hash_value = "test_create_item"
    item = dedupe_sqs.create_item(hash_value)

    assert (
        item["consumption_count"] == 1
        and item["message_id"] == hash_value
        and item["status"] == "IN_PROGRESS"
        and "updated" in item
    )


def test_conditional_create_item(dedupe_sqs):
    """
    Ensure the same item can't be inserted twice
    """
    hash_value = "test_conditional_create_item"
    dedupe_sqs.create_item(hash_value)
    with pytest.raises(ClientError) as e:
        dedupe_sqs.create_item(hash_value)

    assert e._excinfo[1].response["Error"]["Code"] == "ConditionalCheckFailedException"


def test_get_item(dedupe_sqs):
    """
    Ensure you can retrieve the item as expected
    """
    hash_value = "test_get_item"
    dedupe_sqs.create_item(hash_value)
    item = dedupe_sqs.get_item(hash_value)

    assert item["message_id"] == hash_value


def test_invalid_get_item(dedupe_sqs):
    """
    Ensure that if you attempt to retrieve a non-existant value it returns
    nothing
    """
    hash_value = "test_invalid_get_item"
    item = dedupe_sqs.get_item(hash_value)
    assert item is None


# def test_update_item(ddb_client, dedupe_sqs):
