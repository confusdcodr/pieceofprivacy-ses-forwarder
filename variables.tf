variable "bucket" {
  description = "The name of the bucket"
  type        = string
}

variable "tags" {
  description = "The tags applied to the bucket"
  type        = map(string)
  default     = {}
}
