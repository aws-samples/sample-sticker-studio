from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    Duration,
    aws_kms as kms,
    aws_s3_deployment as s3deploy,
    aws_s3 as s3,
    Stack,
    Tags,
)
from constructs import Construct
from config.environment import EnvironmentConfig


class BucketStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: EnvironmentConfig,
        **kwargs,
    ) -> None:

        super().__init__(scope, id, **kwargs)

        # Store configuration
        self.config = config

        # Create KMS key for S3 encryption
        bucket_key = kms.Key(
            self,
            "BucketEncryptionKey",
            description=f"KMS key for S3 bucket encryption - {config.environment.value}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY if config.environment.value == 'dev' else RemovalPolicy.RETAIN,
        )

        # Create main bucket with enhanced security
        bucket_name = config.get_resource_name("image-storage").lower()
        storage_bucket = s3.Bucket(
            self,
            "ImageStorageBucket",
            bucket_name=f"{bucket_name}-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY if config.environment.value == 'dev' else RemovalPolicy.RETAIN,
            enforce_ssl=True,
            auto_delete_objects=config.environment.value == 'dev',
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=bucket_key,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteIncompleteMultipartUploads",
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                    enabled=True,
                ),
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(30),
                    enabled=True,
                ),
            ],
        )
        
        # Add CORS configuration with environment-specific origins
        storage_bucket.add_cors_rule(
            allowed_methods=[
                s3.HttpMethods.GET,
                s3.HttpMethods.HEAD,
                s3.HttpMethods.PUT,
                s3.HttpMethods.POST,
            ],
            allowed_origins=config.security.cors_allowed_origins,
            allowed_headers=["*"],
            max_age=3000
        )

        # Upload fonts to S3
        s3deploy.BucketDeployment(
            self,
            "DeployFonts",
            sources=[s3deploy.Source.asset("./fonts")],
            destination_bucket=storage_bucket,
            destination_key_prefix="fonts/",
        )

        # Apply standard tags
        Tags.of(storage_bucket).add("Environment", config.environment.value)
        Tags.of(storage_bucket).add("Project", "StickerStudio")
        Tags.of(storage_bucket).add("CostCenter", "Engineering")
        Tags.of(bucket_key).add("Environment", config.environment.value)
        Tags.of(bucket_key).add("Project", "StickerStudio")
        Tags.of(bucket_key).add("CostCenter", "Engineering")

        # Export values for cross-stack references
        CfnOutput(
            self,
            "ImageStorageBucketName",
            value=storage_bucket.bucket_name,
            export_name=f"{self.stack_name}-ImageStorageBucketName",
            description="Name of the S3 bucket for image storage"
        )

        CfnOutput(
            self,
            "ImageStorageBucketArn",
            value=storage_bucket.bucket_arn,
            export_name=f"{self.stack_name}-ImageStorageBucketArn",
            description="ARN of the S3 bucket for image storage"
        )

        CfnOutput(
            self,
            "BucketEncryptionKeyArn",
            value=bucket_key.key_arn,
            export_name=f"{self.stack_name}-BucketEncryptionKeyArn",
            description="ARN of the KMS key used for bucket encryption"
        )

        # Store references for other stacks
        self.storage_bucket = storage_bucket
        self.storage_bucket_name = storage_bucket.bucket_name
        self.storage_bucket_arn = storage_bucket.bucket_arn
        self.encryption_key = bucket_key
        self.bucket_key_arn = bucket_key.key_arn
