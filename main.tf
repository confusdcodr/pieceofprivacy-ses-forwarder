#####################
###  DATA SOURCES ###
#####################
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

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
  name = "pieceofprivacy-ses-forwarder"
}

resource "aws_sqs_queue" "this" {
  name = "pieceofprivacy-ses-forwarder"
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
  rule_set_name = "pieceofprivacy-ses-forwarder"
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
  }

  sns_action {
    topic_arn = aws_sns_topic.this.arn
    position  = 2
  }
}

# Set the created rule set as the active rule set
#resource "aws_ses_active_receipt_rule_set" "this" {
#  rule_set_name = aws_ses_receipt_rule_set.this.id
#}
