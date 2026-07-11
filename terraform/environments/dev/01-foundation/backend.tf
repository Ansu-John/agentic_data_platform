# State must be stored remotely in S3 with DynamoDB state locking to 
# prevent concurrent modifications during automated CI/CD runs.

terraform {
  backend "s3" {
    bucket         = "dataplatform-dev-tfstate-bucket" # Pre-create this manually
    key            = "dev/01-foundation/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-state-lock" # Pre-create this manually
    encrypt        = true
  }
}