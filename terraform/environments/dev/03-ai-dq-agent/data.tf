data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/02-data-pipeline/terraform.tfstate"
    region = var.aws_region
  }
}

data "terraform_remote_state" "data_pipeline" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/02-data-pipeline/terraform.tfstate"
    region = var.aws_region
  }
}