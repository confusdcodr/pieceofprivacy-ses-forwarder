#####################
###   S3 Bucket   ###
#####################
variable "bucket" {
  description = "The name of the bucket"
  type        = string
}

#####################
###      SES      ###
#####################
variable "domain" {
  description = "The domain to verify. Requires that you own the domain"
  type        = string
}

variable "zone_id" {
  description = "Zone ID of the route53 hosted zone to add the record(s) to"
  type        = string
}

#####################
###     LAMBDA    ###
#####################
variable "mail_recipient" {
  description = "The email address to forward the emails to"
  type        = string
}

variable "mail_sender" {
  description = "The email address which forwarded emails come from"
  type        = string
}

variable "tags" {
  description = "The tags applied to the bucket"
  type        = map(string)
  default     = {}
}
