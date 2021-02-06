#####################
###  DATA SOURCES ###
#####################
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

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
  rule_set_name = var.project_name
}

# receipt rule to store emails in S3 and then publish to sns
resource "aws_ses_receipt_rule" "this" {
  name          = "forward-emails-to-s3-sns"
  rule_set_name = aws_ses_receipt_rule_set.this.id
  recipients    = []
  enabled       = true
  scan_enabled  = true

  s3_action {
    bucket_name       = var.bucket
    object_key_prefix = "email/"
    position          = 1
    topic_arn         = var.topic_arn
  }
}

# Set the created rule set as the active rule set
resource "aws_ses_active_receipt_rule_set" "this" {
  rule_set_name = aws_ses_receipt_rule_set.this.id
}
