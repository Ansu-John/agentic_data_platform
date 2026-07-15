terraform {
  backend "s3" {
    bucket         = "dataplatform-dev-tfstate-bucket" # Shared enterprise state bucket
    key            = "dev/03-ai-dq-agent/terraform.tfstate" # NEW: Dedicated key for Phase 3 state
    region         = "ap-south-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
