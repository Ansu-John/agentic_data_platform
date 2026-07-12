# Fetch current AWS account details for ARN construction if needed
data "aws_caller_identity" "current" {}

# Read outputs from Phase 1 Foundation
data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/01-foundation/terraform.tfstate"
    region = var.aws_region
  }
}