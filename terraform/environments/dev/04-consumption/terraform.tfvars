aws_region   = "ap-south-1"
environment  = "dev"
project_name = "dataplatform"
tags = {
  Project     = "AI-Data-Platform"
  Environment = "dev"
  Phase       = "Phase-4-Consumption"
  ManagedBy   = "Terraform"
}

api_image_tag = "v1.0.0"
ui_image_tag  = "v1.0.0"

# The email address that will receive SNS alerts when data is marked NON_COMPLIANT
alert_email = "ansujohn.sg@gmail.com"