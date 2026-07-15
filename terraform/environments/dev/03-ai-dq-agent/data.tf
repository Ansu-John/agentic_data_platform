data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = var.terraform_state_bucket
    key    = "dev/01-foundation/terraform.tfstate" 
    region = var.aws_region
  }
}

data "terraform_remote_state" "data_pipeline" {
  backend = "s3"
  config = {
    bucket = var.terraform_state_bucket
    key    = "dev/02-data-pipeline/terraform.tfstate"
    region = var.aws_region
  }
}

data "terraform_remote_state" "ai-dq-agent" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/03-ai-dq-agent/terraform.tfstate"
    region = var.aws_region
  }
}