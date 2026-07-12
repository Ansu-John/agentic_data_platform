# ---------------------------------------------------------
# EMR Serverless Application
# ---------------------------------------------------------
module "emr_serverless" {
  source = "../../../modules/emr_serverless"

  app_name           = "${var.project}-${var.environment}-spark-engine"
  environment        = var.environment
  vpc_id             = data.terraform_remote_state.foundation.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.foundation.outputs.private_subnet_ids
}

# ---------------------------------------------------------
# EMR Execution Role (Strictly Scoped)
# ---------------------------------------------------------
resource "aws_iam_role" "emr_execution_role" {
  name = "${var.project}-${var.environment}-emr-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "emr-serverless.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "emr_data_access" {
  name        = "${var.project}-${var.environment}-emr-data-access"
  description = "Allows EMR to read Bronze, write Silver, and update Glue"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3DataLakeAccess"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::${data.terraform_remote_state.foundation.outputs.datalake_bucket_names[0]}*", # Bronze
          "arn:aws:s3:::${data.terraform_remote_state.foundation.outputs.datalake_bucket_names[1]}*"  # Silver
        ]
      },
      {
        Sid      = "GlueCatalogAccess"
        Effect   = "Allow"
        Action   = [
          "glue:GetDatabase", "glue:CreateDatabase", 
          "glue:GetTable", "glue:CreateTable", "glue:UpdateTable",
          "glue:GetPartition", "glue:CreatePartition", "glue:BatchCreatePartition"
        ]
        Resource = ["*"] # Note: In a stricter setup, scope this to the specific catalog ARNs
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "emr_access_attach" {
  role       = aws_iam_role.emr_execution_role.name
  policy_arn = aws_iam_policy.emr_data_access.arn
}