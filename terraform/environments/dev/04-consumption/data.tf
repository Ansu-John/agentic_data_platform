data "aws_caller_identity" "current" {}

# Fetch Foundation Networking (VPC, Subnets)
data "terraform_remote_state" "foundation" {
  backend = "s3" # Change to "local" if you aren't using S3 state yet
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/01-foundation/terraform.tfstate"
    region = "ap-south-1"
  }
}

# Fetch ECS Cluster and Security Groups from Phase 3
data "terraform_remote_state" "agent" {
  backend = "s3" # Change to "local" if you aren't using S3 state yet
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/03-ai-dq-agent/terraform.tfstate"
    region = "ap-south-1"
  }
}