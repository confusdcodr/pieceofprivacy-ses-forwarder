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
