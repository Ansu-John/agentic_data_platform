data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/01-foundation/terraform.tfstate"
    region = var.aws_region
  }
}

data "terraform_remote_state" "catalog" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/02a-ingestion-catalog/terraform.tfstate"
    region = var.aws_region
  }
}
