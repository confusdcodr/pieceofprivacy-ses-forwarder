import json
import uuid

import boto3
import pytest


def test_send_email(s3_email, monkeypatch):
    # setup environment variables
    src = "from@pieceofprivacy.com"
    dest = "to@pieceofprivacy.com"
    monkeypatch.setenv("MAIL_SENDER", src)
    monkeypatch.setenv("MAIL_RECIPIENT", dest)

    response = s3_email.send_email()
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
