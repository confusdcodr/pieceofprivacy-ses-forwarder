import json
import uuid

import boto3
import pytest
from ses_forwarder.ses_forwarder.S3Email import S3Email


def test_extract_headers(s3_email, monkeypatch):
    # setup environment variables
    src = "from@pieceofprivacy.com"
    dest = "to@pieceofprivacy.com"
    monkeypatch.setenv("MAIL_SENDER", src)
    monkeypatch.setenv("MAIL_RECIPIENT", dest)

    email = s3_email.extract_headers()
    assert s3_email.src == src and s3_email.dest == dest and email is not None


def test_send_email(s3_email, monkeypatch):
    # setup environment variables
    src = "from@pieceofprivacy.com"
    dest = "to@pieceofprivacy.com"
    monkeypatch.setenv("MAIL_SENDER", src)
    monkeypatch.setenv("MAIL_RECIPIENT", dest)

    s3_email.extract_headers()
    response = s3_email.send_email()
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
