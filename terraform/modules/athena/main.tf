resource "aws_s3_bucket" "athena_results" {
  bucket        = "dataplatform-${var.environment}-athena-results-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results_enc" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_athena_workgroup" "nlq_workgroup" {
  name = "dataplatform_${var.environment}_nlq_workgroup"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    # Guardrail against runaway costs from LLM loops by enforcing a 10MB bytes-scanned limit per query (adjust for real datasets)
    bytes_scanned_cutoff_per_query = 104857600 

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"
      encryption_configuration {
        encryption_option = "SSE_KMS"
        kms_key_arn       = var.kms_key_arn
      }
    }
  }
}

data "aws_caller_identity" "current" {}