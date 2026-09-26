# Only use the imports if the resources are already created
import {
  to = aws_iam_role.emr_execution_role
  id = "dataplatform-dev-emr-exec-role"
}

import {
  to = aws_iam_role.step_functions_role
  id = "dataplatform-dev-sfn-role"
}

import {
  to = aws_db_subnet_group.default
  id = "dataplatform-dev-db-subnet-group"
}

import {
  to = module.glue_catalog.aws_glue_catalog_database.this
  id = "${data.aws_caller_identity.current.account_id}:dataplatform_dev_ai_catalog"
}

import {
  to = module.ingest_trigger.aws_iam_role.this
  id = "dataplatform-dev-ingest-trigger-role"
}

import {
  to = module.ingest_trigger.aws_iam_policy.s3_read
  id = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/dataplatform-dev-ingest-trigger-s3-read-policy"
}

import {
  to = aws_ssm_parameter.db_host
  id = "/dataplatform/dev/db_host"
}

import {
  to = module.db_init_lambda.aws_iam_role.lambda_role
  id = "dataplatform-dev-db-init-role"
}