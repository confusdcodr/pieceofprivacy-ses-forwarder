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

variable "tags" {
  description = "The tags applied to the bucket"
  type        = map(string)
  default     = {}
}
