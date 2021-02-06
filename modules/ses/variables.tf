variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "domain" {
  description = "The domain to verify. Requires that you own the domain"
  type        = string
}

variable "zone_id" {
  description = "Zone ID of the route53 hosted zone to add the record(s) to"
  type        = string
}


variable "bucket" {
  description = "The name of the bucket to dump emails to"
  type        = string
}

variable "topic_arn" {
  description = "The ARN of the sns topic to notify once the email has been uploaded to the bucket"
  type        = string
}
