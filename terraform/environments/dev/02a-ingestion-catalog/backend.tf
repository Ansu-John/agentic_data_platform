terraform {
  backend "s3" {
    bucket         = "dataplatform-dev-tfstate-bucket"
    key            = "dev/02a-ingestion-catalog/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}