#####################
###  DATA SOURCES ###
#####################
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  project_name = "pieceofprivacy-ses-forwarder"
}

#####################
###   S3 Bucket   ###
#####################
resource "aws_s3_bucket" "this" {
  bucket = var.bucket

  acl           = "private"
  policy        = data.aws_iam_policy_document.ses_s3_policy.json
  force_destroy = false

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  lifecycle_rule {
    enabled = true

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days                         = 90
      expired_object_delete_marker = true
    }

    noncurrent_version_expiration {
      days = 45
    }
  }

  tags = var.tags
}

resource "aws_s3_bucket_public_access_block" "example" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

}

data "aws_iam_policy_document" "ses_s3_policy" {
  statement {
    sid = "AllowSESPuts"

    principals {
      type        = "Service"
      identifiers = ["ses.amazonaws.com"]
    }

    actions = [
      "s3:PutObject",
    ]

    resources = [
      "arn:aws:s3:::${var.bucket}/*"
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:Referer"

      values = [
        data.aws_caller_identity.current.account_id
      ]
    }
  }
}

#####################
###    SNS/SQS    ###
#####################
resource "aws_sns_topic" "this" {
  name = local.project_name
}

locals {
  sqs_template_vars = {
    region     = data.aws_region.current.name,
    account_id = data.aws_caller_identity.current.account_id
    queue_name = local.project_name
    topic_name = local.project_name
  }
}

resource "aws_sqs_queue" "this" {
  name   = local.project_name
  policy = templatefile("${path.module}/templates/sqs-access-policy.json", local.sqs_template_vars)
}

resource "aws_sns_topic_subscription" "user_updates_sqs_target" {
  topic_arn = aws_sns_topic.this.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.this.arn
}

#####################
###      SES      ###
#####################
# Good Resource
# https://github.com/trussworks/terraform-aws-ses-domain

# lookup the provided route53 zone
data "aws_route53_zone" "this" {
  zone_id = var.zone_id
}

# add the domain to SES
resource "aws_ses_domain_identity" "this" {
  domain = var.domain
}

# add the domain verification record to Route53
resource "aws_route53_record" "domain_verification" {
  zone_id = data.aws_route53_zone.this.zone_id
  name    = "_amazonses.${var.domain}"
  type    = "TXT"
  ttl     = "1800"
  records = [aws_ses_domain_identity.this.verification_token]
}

# hold until the domain has been verified
resource "aws_ses_domain_identity_verification" "this" {
  domain = aws_ses_domain_identity.this.id

  depends_on = [aws_route53_record.domain_verification]
}

# receiving MX Record
resource "aws_route53_record" "mx_receive" {
  name    = var.domain
  zone_id = data.aws_route53_zone.this.zone_id
  type    = "MX"
  ttl     = "600"
  records = ["10 inbound-smtp.${data.aws_region.current.name}.amazonaws.com"]
}

# receipt Rule Set
resource "aws_ses_receipt_rule_set" "this" {
  rule_set_name = local.project_name
}

# receipt rule to store emails in S3 and then publish to sns
resource "aws_ses_receipt_rule" "this" {
  name          = "forward-emails-to-s3-sns"
  rule_set_name = aws_ses_receipt_rule_set.this.id
  recipients    = []
  enabled       = true
  scan_enabled  = true

  s3_action {
    bucket_name       = aws_s3_bucket.this.id
    object_key_prefix = "email/"
    position          = 1
    topic_arn         = aws_sns_topic.this.arn
  }
}

# Set the created rule set as the active rule set
resource "aws_ses_active_receipt_rule_set" "this" {
  rule_set_name = aws_ses_receipt_rule_set.this.id
}

#####################
###    LAMBDA     ###
#####################

module "lambda" {
  source = "git::https://github.com/plus3it/terraform-aws-lambda.git?ref=v1.2.0"

  function_name = local.project_name
  description   = ""
  handler       = "main.handler"
  runtime       = "python3.7"
  timeout       = 30

  source_path = "${path.module}/handlers/ses_forwarder"

  # execution policy
  policy = {
    json = data.aws_iam_policy_document.lambda_ses_forwarder.json
  }

  environment = {
    variables = {
      MAIL_RECIPIENT = var.mail_recipient
      MAIL_SENDER    = var.mail_sender
      REGION         = data.aws_region.current.name
      DEDUPE_TABLE   = aws_dynamodb_table.sqs_dedupe_table.id
      LAMBDA_TIMEOUT = 30
    }
  }
}

# invocation policy
resource "aws_lambda_permission" "this" {
  action         = "lambda:InvokeFunction"
  function_name  = module.lambda.function_name
  principal      = "sqs.amazonaws.com"
  source_account = data.aws_caller_identity.current.account_id
}

# invocation trigger
resource "aws_lambda_event_source_mapping" "this" {
  event_source_arn                   = aws_sqs_queue.this.arn
  function_name                      = module.lambda.function_arn
  batch_size                         = 1 #change this to 10 later
  maximum_batching_window_in_seconds = 0 # change this to 60 later
}

data "aws_iam_policy_document" "lambda_ses_forwarder" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "arn:aws:s3:::${aws_s3_bucket.this.id}/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "ses:SendRawEmail",
    ]

    resources = [
      "arn:aws:ses:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:identity/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl"
    ]

    resources = [
      aws_sqs_queue.this.arn
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem"
    ]

    resources = [
      aws_dynamodb_table.sqs_dedupe_table.arn
    ]
  }
}

####################
###   DYNAMODB   ###
####################
resource "aws_dynamodb_table" "sqs_dedupe_table" {
  name           = "pieceofprivacy-sqs-dedupe"
  billing_mode   = "PROVISIONED"
  hash_key       = "message_id"
  read_capacity  = 5
  write_capacity = 5

  attribute {
    name = "message_id"
    type = "S"
  }

  #ttl {
  #  attribute_name = "TimeToExist"
  #  enabled        = true
  #}

  tags = var.tags
}
