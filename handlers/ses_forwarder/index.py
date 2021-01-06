import email
import json
import os
import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
from botocore.exceptions import ClientError

region = os.environ["REGION"]
client_s3 = boto3.client("s3")
client_ses = boto3.client("ses", region)

DEBUG = False


def get_message_from_s3(bucket_name, key):
    object_http_path = f"http://s3.console.aws.amazon.com/s3/object/{bucket_name}/{key}?region={region}"

    # Get the email object from the S3 bucket.
    object_s3 = client_s3.get_object(Bucket=bucket_name, Key=key)

    # Read the content of the message.
    file = object_s3["Body"].read()

    file_dict = {"file": file, "path": object_http_path}

    return file_dict


def alter_headers(file_dict):
    # Parse the email body.
    mail_obj = email.message_from_string(file_dict["file"].decode("utf-8"))

    if DEBUG:
        for key in mail_obj.keys():
            print(f"{key}:{mail_obj[key]}")

    orig_src_email = mail_obj["From"]
    orig_dest_email = mail_obj["To"]
    new_src_email = os.environ["MAIL_SENDER"]
    new_dest_email = os.environ["MAIL_RECIPIENT"]

    info_message = (
        f"Initially, {orig_src_email} emailed {orig_dest_email}. "
        f"The email is being updated to be from {new_src_email} "
        f"with a destination of {new_dest_email}"
    )
    print(info_message)

    # Remove headers
    del mail_obj["DKIM-Signature"]
    del mail_obj["From"]
    del mail_obj["To"]
    del mail_obj["Reply-To"]
    del mail_obj["Return-Path"]
    del mail_obj["Sender"]

    # Replace headers with new values
    mail_obj["Reply-To"] = orig_src_email
    mail_obj["From"] = new_src_email
    mail_obj["To"] = new_dest_email

    # setup message object
    message = {
        "Source": new_src_email,
        "Destinations": new_dest_email,
        "Data": mail_obj.as_string(),
    }

    return message


def send_email(message):
    # Send the email.
    try:
        # Provide the contents of the email.
        response = client_ses.send_raw_email(
            Source=message["Source"],
            Destinations=[message["Destinations"]],
            RawMessage={"Data": message["Data"]},
        )

    # Display an error if something goes wrong.
    except ClientError as e:
        output = e.response["Error"]["Message"]
    else:
        output = "Email sent! Message ID: " + response["MessageId"]

    return output


def handler(event, context):
    # Get the unique ID of the message. This corresponds to the s3 key.
    print(f"Event received: {json.dumps(event)}")
    for record in event.get("Records"):
        sqs_message_id = record.get("messageId")
        sqs_receipt_handle = record.get("receiptHandle")
        sqs_message_body = json.loads(record.get("body"))

        sns_message_body = json.loads(sqs_message_body.get("Message"))

        bucket_name = sns_message_body["receipt"]["action"]["bucketName"]
        key = sns_message_body["receipt"]["action"]["objectKey"]

        # Retrieve the file from the S3 bucket.
        file_dict = get_message_from_s3(bucket_name, key)

        # Create the message.
        message = alter_headers(file_dict)

        # Send the email and print the result.
        result = send_email(message)
        print(result)


def main():
    with open("../tests/events/test_event1.json") as json_file:
        event = json.load(json_file)

    handler(event, None)


if __name__ == "__main__":
    main()
