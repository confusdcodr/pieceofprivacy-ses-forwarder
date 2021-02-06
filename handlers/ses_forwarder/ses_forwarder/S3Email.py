import email
import os
import string
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3


class S3Email:
    """
    Class representing the email retrieve from S3. This class handles redirecting the email
    from it original destination to its new destination

    Attrs:
        orig_from: Who the email originally came from
        orig_to: Who the email was originally destined to
        forward_from (str): The from field for the forwarded email (this is a generic email)
        forward_to (List[str]): The email address to forward the email to
    """

    def __init__(self, bucket_name: str, key: str, region: str = "us-east-1"):
        self.s3_client = boto3.client("s3")
        self.ses_client = boto3.client("ses", region)
        s3_object = self.s3_client.get_object(Bucket=bucket_name, Key=key)
        self.email = email.message_from_string(s3_object["Body"].read().decode("utf-8"))

        # Save the original source and destination
        self._orig_from = self.clean_string(self.email.get("From"))
        self._orig_to = self.clean_string(self.email.get("To"))

        # Setup the generic from address for the forwarded email
        self._forward_from = os.environ["MAIL_SENDER"]
        self._forward_to = []

        self.remove_headers()

    @property
    def orig_from(self):
        return self._orig_from

    @property
    def orig_to(self):
        return self._orig_to

    @property
    def forward_from(self):
        return self._forward_from

    @property
    def forward_to(self):
        return self._forward_to

    def add_forward_to(self, value):
        if value not in self._forward_to:
            self._forward_to.append(value)

    def clean_string(self, value):
        # using translate() to remove bad_chars
        delete_dict = {sp_character: "" for sp_character in string.punctuation}
        delete_dict[" "] = ""
        delete_dict.pop("@")
        delete_dict.pop(".")
        table = str.maketrans(delete_dict)

        return value.translate(table)

    def remove_headers(self):
        # remove unecessary headers
        self.email.__delitem__("To")
        self.email.__delitem__("From")
        self.email.__delitem__("Sender")
        self.email.__delitem__("Reply-To")
        self.email.__delitem__("Return-Path")
        self.email.__delitem__("DKIM-Signature")

    def send_email(self):
        # Replace headers with new values
        self.email.add_header("Reply-To", self.orig_from)
        self.email.add_header("From", self.forward_from)

        for dest in self.forward_to:
            self.email.add_header("To", dest)

        response = self.ses_client.send_raw_email(
            Source=self.forward_from,
            Destinations=self.forward_to,
            RawMessage={"Data": self.email.as_string()},
        )

        return response
