#####################
###  DATA SOURCES ###
#####################
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  project_name = "pieceofprivacy-ses-forwarder"
  timeout      = 30
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

# create an sns topic
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

# create a sqs queue that the sns topic will delivery to
resource "aws_sqs_queue" "this" {
  name                       = local.project_name
  visibility_timeout_seconds = local.timeout

  policy                     = templatefile("${path.module}/templates/sqs-access-policy.json", local.sqs_template_vars)
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 4
  })
}

# subscribe the sqs queue to the sns topic
resource "aws_sns_topic_subscription" "user_updates_sqs_target" {
  topic_arn = aws_sns_topic.this.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.this.arn
}

locals {
  sqs_dlq_template_vars = {
    region     = data.aws_region.current.name,
    account_id = data.aws_caller_identity.current.account_id
    queue_name = local.project_name
  }
}

# create a dead letter queue for messages that
# aren't processed within the regular queue
resource "aws_sqs_queue" "dlq" {
  name                      = "${local.project_name}-dlq"
  message_retention_seconds = 1209600 #14 days
  policy                    = templatefile("${path.module}/templates/sqs-dlq-access-policy.json", local.sqs_dlq_template_vars)
}

#####################
###      SES      ###
#####################
module "ses_forwarder" {
  source = "./modules/ses"

  providers = {
    aws = aws
  }

  project_name = local.project_name
  zone_id      = var.zone_id
  domain       = var.domain
  bucket       = aws_s3_bucket.this.id
  topic_arn    = aws_sns_topic.this.arn
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
  timeout       = local.timeout

  source_path = "${path.module}/handlers/ses_forwarder"

  # execution policy
  policy = {
    json = data.aws_iam_policy_document.lambda_ses_forwarder.json
  }

  environment = {
    variables = {
      LAMBDA_TIMEOUT = local.timeout
      MAIL_SENDER    = var.mail_sender
      REGION         = data.aws_region.current.name
      LOOKUP_TABLE   = aws_dynamodb_table.lookup_table.id
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
      aws_dynamodb_table.lookup_table.arn
    ]
  }
}

####################
###   DYNAMODB   ###
####################
resource "aws_dynamodb_table" "lookup_table" {
  name           = "${local.project_name}-lookup"
  billing_mode   = "PROVISIONED"
  hash_key       = "email"
  range_key      = "destination"
  read_capacity  = 5
  write_capacity = 5

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "destination"
    type = "S"
  }

  tags = var.tags
}

locals {
  email  = element(split("@", var.mail_sender), 0)
  domain = element(split("@", var.mail_sender), 1)

  lookup_table_template_vars = {
    hash_value  = "*@${local.domain}",
    range_value = var.mail_recipient
  }
}

#resource "aws_dynamodb_table_item" "this" {
#  table_name = aws_dynamodb_table.lookup_table.name
#  hash_key   = aws_dynamodb_table.lookup_table.hash_key
#  item       = templatefile("${path.module}/templates/ddb-lookup-table-item.json", local.lookup_table_template_vars)
#}
