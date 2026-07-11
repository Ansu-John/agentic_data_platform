package test

import (
	"testing"
	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestFoundationPhase1(t *testing.T) {
	t.Parallel()

	awsRegion := "ap-south-1"

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../terraform/environments/dev/01-foundation",
	})

	// Defer the teardown to run at the end of the test
	defer terraform.Destroy(t, terraformOptions)

	// Apply the infrastructure
	terraform.InitAndApply(t, terraformOptions)

	// Assert S3 buckets exist and have versioning enabled
	bronzeBucketName := "dataplatform-dev-s3-aps1-bronze"
	aws.AssertS3BucketExists(t, awsRegion, bronzeBucketName)
	
	versioningStatus := aws.GetS3BucketVersioning(t, awsRegion, bronzeBucketName)
	assert.Equal(t, "Enabled", versioningStatus)
}