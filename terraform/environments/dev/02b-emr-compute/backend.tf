terraform {
  backend "s3" {
    bucket         = "dataplatform-dev-tfstate-bucket"
    key            = "dev/02b-emr-compute/terraform.tfstate" # Isolated state key
    region         = "ap-south-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}