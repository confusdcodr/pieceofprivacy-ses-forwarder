# pieceofprivacy-ses-forwarder
Terraform module for PieceOfPrivacy.com which setups route53, ses, and lambda to forward emails to the given destination

<!-- BEGIN TFDOCS -->
## Requirements

| Name | Version |
|------|---------|
| terraform | ~> 0.14.2 |
| aws | ~> 3.20 |

## Providers

| Name | Version |
|------|---------|
| aws | ~> 3.20 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket | The name of the bucket | `string` | n/a | yes |
| domain | The domain to verify. Requires that you own the domain | `string` | n/a | yes |
| zone\_id | Zone ID of the route53 hosted zone to add the record(s) to | `string` | n/a | yes |
| tags | The tags applied to the bucket | `map(string)` | `{}` | no |

## Outputs

No output.

<!-- END TFDOCS -->
