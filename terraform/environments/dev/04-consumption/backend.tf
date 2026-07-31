terraform {
  backend "s3" {

    bucket         = "dataplatform-dev-terraform-state-bucket" # Shared enterprise state bucket
    key            = "dev/04-consumption/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}