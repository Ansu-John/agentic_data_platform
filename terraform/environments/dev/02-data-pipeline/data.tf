# Fetch current AWS account details for ARN construction if needed
data "aws_caller_identity" "current" {}

# -------------------------------------------------------------------
# Data Sources & Cross-Phase State Wiring
# -------------------------------------------------------------------
# Read outputs from Phase 1 Foundation
data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/01-foundation/terraform.tfstate"
    region = var.aws_region
  }
}

# Read outputs from Phase 2 Data pipeline
data "terraform_remote_state" "emr_compute" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/02-data-pipeline/terraform.tfstate"
    region = var.aws_region
  }
}