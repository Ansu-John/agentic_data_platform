resource "aws_s3_bucket" "datalake_zones" {
  count  = length(var.zones)
  bucket = "${var.bucket_prefix}-${var.zones[count.index]}"
}

resource "aws_s3_bucket_public_access_block" "datalake_public_block" {
  count                   = length(aws_s3_bucket.datalake_zones)
  bucket                  = aws_s3_bucket.datalake_zones[count.index].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "datalake_versioning" {
  count  = length(aws_s3_bucket.datalake_zones)
  bucket = aws_s3_bucket.datalake_zones[count.index].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datalake_encryption" {
  count  = length(aws_s3_bucket.datalake_zones)
  bucket = aws_s3_bucket.datalake_zones[count.index].id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}