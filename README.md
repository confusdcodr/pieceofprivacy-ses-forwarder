# pieceofprivacy-ses-forwarder

Terraform module for PieceOfPrivacy.com which setups route53, ses, and lambda to forward emails to the given destination

## Architecture

![Architecture](https://github.com/confusdcodr/pieceofprivacy-ses-forwarder/blob/main/_docs/architecture.png?raw=true)

## Prerequisites

* Your own domain
* An aws route53 zone setup for your domain
* An aws ses service setup for production use (i.e., not in sandbox mode)

<!-- BEGIN TFDOCS -->
## Requirements

| Name | Version |
|------|---------|
| terraform | ~> 0.14.2 |
| aws | ~> 3.22 |
| external | ~> 2.0 |
| null | ~> 3.0 |

## Providers

| Name | Version |
|------|---------|
| aws | ~> 3.22 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket | The name of the bucket | `string` | n/a | yes |
| domain | The domain to verify. Requires that you own the domain | `string` | n/a | yes |
| mail\_recipient | The email address to forward the emails to | `string` | n/a | yes |
| mail\_sender | The email address which forwarded emails come from | `string` | n/a | yes |
| zone\_id | Zone ID of the route53 hosted zone to add the record(s) to | `string` | n/a | yes |
| tags | The tags applied to the bucket | `map(string)` | `{}` | no |

## Outputs

No output.

<!-- END TFDOCS -->
