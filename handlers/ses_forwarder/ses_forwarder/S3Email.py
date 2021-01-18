import email
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3


class S3Email:
    def __init__(self, bucket_name: str, key: str, region: str = "us-east-1"):
        self.s3_client = boto3.client("s3")
        self.ses_client = boto3.client("ses", region)

        s3_object = self.s3_client.get_object(Bucket=bucket_name, Key=key)
        self.email = email.message_from_string(s3_object["Body"].read().decode("utf-8"))

    def extract_headers(self):
        # Save source and destination
        self.reply_to = self.email.get("From")
        self.src = os.environ["MAIL_SENDER"]
        self.dest = os.environ["MAIL_RECIPIENT"]

        # Remove unnecessary headers
        self.email.__delitem__("To")
        self.email.__delitem__("From")
        self.email.__delitem__("Sender")
        self.email.__delitem__("Reply-To")
        self.email.__delitem__("Return-Path")
        self.email.__delitem__("DKIM-Signature")

        # Replace headers with new values
        self.email.add_header("Reply-To", self.reply_to)
        self.email.add_header("From", self.src)
        self.email.add_header("To", self.dest)

        return self.email

    def send_email(self):
        response = self.ses_client.send_raw_email(
            Source=self.src,
            Destinations=[self.dest],
            RawMessage={"Data": self.email.as_string()},
        )

        return response
