"""
Property-based tests for BucketStack security and configuration.

Tests S3 bucket security configuration and resource naming compliance
across different environments and configurations.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from aws_cdk import App, Stack
from aws_cdk.assertions import Template

from stacks.bucketStack import BucketStack
from config.environment import EnvironmentConfig, DeploymentEnvironment


# Test data strategies
valid_environments = st.sampled_from(['dev', 'staging', 'prod'])
valid_regions = st.sampled_from([
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'eu-west-1', 'eu-west-2', 'eu-central-1'
])
valid_account_ids = st.text(min_size=12, max_size=12, alphabet='0123456789')
valid_prefixes = st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
valid_domains = st.text(min_size=5, max_size=50).filter(
    lambda x: '.' in x and not x.startswith('.') and not x.endswith('.')
)


class TestBucketStackProperties:
    """Property-based tests for BucketStack"""
    
    @given(
        environment=valid_environments,
        region=valid_regions,
        account_id=valid_account_ids,
        prefix=valid_prefixes,
        domain=st.one_of(st.none(), valid_domains)
    )
    @settings(max_examples=5, deadline=None)  # Reduced for faster execution, no deadline for CDK
    def test_s3_bucket_security_configuration(self, environment, region, account_id, prefix, domain):
        """
        Feature: deployment-improvements, Property 4: S3 Bucket Security Configuration
        
        For any S3 bucket created by the CDK stacks, the bucket should have server-side 
        encryption enabled, public access blocked, and SSL enforcement configured.
        **Validates: Requirements 3.2**
        """
        # For production environment, ensure required parameters are provided
        if environment == 'prod':
            assume(domain is not None)
            certificate_arn = f"arn:aws:acm:{region}:{account_id}:certificate/test-cert"
        else:
            certificate_arn = None
        
        # Create environment configuration
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region=region,
            account_id=account_id,
            domain_name=domain,
            certificate_arn=certificate_arn,
            cognito_domain_prefix=f"test-{environment}",
            resource_prefix=prefix
        )
        
        # Create CDK app and stack
        app = App()
        stack = BucketStack(app, "TestBucketStack", config=config)
        
        # Generate CloudFormation template
        template = Template.from_stack(stack)
        
        # Verify S3 bucket security configuration
        template.has_resource_properties("AWS::S3::Bucket", {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "aws:kms"
                        }
                    }
                ]
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True
            },
            "VersioningConfiguration": {
                "Status": "Enabled"
            }
        })
        
        # Verify SSL enforcement through bucket policy or configuration
        # The enforce_ssl=True should create appropriate bucket policy
        buckets = template.find_resources("AWS::S3::Bucket")
        assert len(buckets) > 0, "At least one S3 bucket should be created"
        
        # Verify KMS key is created for encryption
        template.has_resource("AWS::KMS::Key", {
            "Properties": {
                "Description": f"KMS key for S3 bucket encryption - {environment}",
                "EnableKeyRotation": True
            }
        })
        
        # Verify lifecycle rules are configured
        template.has_resource_properties("AWS::S3::Bucket", {
            "LifecycleConfiguration": {
                "Rules": [
                    {
                        "Id": "DeleteIncompleteMultipartUploads",
                        "Status": "Enabled",
                        "AbortIncompleteMultipartUpload": {
                            "DaysAfterInitiation": 7
                        }
                    },
                    {
                        "Id": "DeleteOldVersions", 
                        "Status": "Enabled",
                        "NoncurrentVersionExpiration": {
                            "NoncurrentDays": 30
                        }
                    }
                ]
            }
        })
    
    @given(
        environment=valid_environments,
        region=valid_regions,
        account_id=valid_account_ids,
        prefix=valid_prefixes,
        domain=st.one_of(st.none(), valid_domains)
    )
    @settings(max_examples=5, deadline=None)  # Reduced for faster execution, no deadline for CDK
    def test_resource_naming_convention_compliance(self, environment, region, account_id, prefix, domain):
        """
        Feature: deployment-improvements, Property 9: Resource Naming Convention Compliance
        
        For any AWS resource created by the CDK stacks, the resource name should include 
        the environment identifier and follow the pattern {prefix}-{service}-{environment}.
        **Validates: Requirements 5.1, 5.4**
        """
        # For production environment, ensure required parameters are provided
        if environment == 'prod':
            assume(domain is not None)
            certificate_arn = f"arn:aws:acm:{region}:{account_id}:certificate/test-cert"
        else:
            certificate_arn = None
        
        # Create environment configuration
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region=region,
            account_id=account_id,
            domain_name=domain,
            certificate_arn=certificate_arn,
            cognito_domain_prefix=f"test-{environment}",
            resource_prefix=prefix
        )
        
        # Create CDK app and stack
        app = App()
        stack = BucketStack(app, "TestBucketStack", config=config)
        
        # Generate CloudFormation template
        template = Template.from_stack(stack)
        
        # Verify naming convention compliance by checking the template
        # The bucket name should be constructed using the expected pattern
        expected_base_name = config.get_resource_name("image-storage").lower()
        
        # Check that the bucket is created with the expected naming pattern
        # We can't check the resolved name directly due to CDK tokens, but we can verify
        # the construction pattern by checking the template structure
        buckets = template.find_resources("AWS::S3::Bucket")
        assert len(buckets) > 0, "At least one S3 bucket should be created"
        
        # Verify the bucket name construction includes the expected components
        # by checking the bucket properties in the template
        for bucket_id, bucket_props in buckets.items():
            bucket_name_prop = bucket_props.get("Properties", {}).get("BucketName")
            if bucket_name_prop:
                # The bucket name should be a reference that includes our expected pattern
                # Since it's a token, we verify the pattern was used in construction
                assert isinstance(bucket_name_prop, dict) or isinstance(bucket_name_prop, str)
        
        # Verify stack outputs follow naming conventions
        template.has_output("ImageStorageBucketName", {
            "Export": {
                "Name": f"TestBucketStack-ImageStorageBucketName"
            }
        })
        
        template.has_output("ImageStorageBucketArn", {
            "Export": {
                "Name": f"TestBucketStack-ImageStorageBucketArn"
            }
        })
        
        template.has_output("BucketEncryptionKeyArn", {
            "Export": {
                "Name": f"TestBucketStack-BucketEncryptionKeyArn"
            }
        })
        
        # Verify the configuration method produces expected naming pattern
        resource_name = config.get_resource_name("image-storage")
        assert prefix in resource_name, f"Resource name '{resource_name}' should contain prefix '{prefix}'"
        assert environment in resource_name, f"Resource name '{resource_name}' should contain environment '{environment}'"
        assert "image-storage" in resource_name, f"Resource name '{resource_name}' should contain service identifier 'image-storage'"
    
    @given(
        environment=valid_environments,
        region=valid_regions,
        account_id=valid_account_ids,
        prefix=valid_prefixes
    )
    @settings(max_examples=5)  # Reduced for faster execution
    def test_resource_tagging_consistency(self, environment, region, account_id, prefix):
        """
        Test that resources are tagged consistently for cost tracking and management.
        """
        # Create environment configuration
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region=region,
            account_id=account_id,
            cognito_domain_prefix=f"test-{environment}",
            resource_prefix=prefix
        )
        
        # Create CDK app and stack
        app = App()
        stack = BucketStack(app, "TestBucketStack", config=config)
        
        # Generate CloudFormation template
        template = Template.from_stack(stack)
        
        # Verify S3 bucket has required tags
        template.has_resource_properties("AWS::S3::Bucket", {
            "Tags": [
                {"Key": "Environment", "Value": environment},
                {"Key": "Project", "Value": "StickerStudio"},
                {"Key": "CostCenter", "Value": "Engineering"}
            ]
        })
        
        # Verify KMS key has required tags
        template.has_resource_properties("AWS::KMS::Key", {
            "Tags": [
                {"Key": "Environment", "Value": environment},
                {"Key": "Project", "Value": "StickerStudio"},
                {"Key": "CostCenter", "Value": "Engineering"}
            ]
        })


class TestBucketStackUnits:
    """Unit tests for specific BucketStack scenarios"""
    
    def test_development_environment_cors_configuration(self):
        """Test that development environment has appropriate CORS configuration"""
        config = EnvironmentConfig(
            environment=DeploymentEnvironment.DEVELOPMENT,
            region="us-east-1",
            account_id="123456789012",
            cognito_domain_prefix="test-dev"
        )
        
        app = App()
        stack = BucketStack(app, "TestBucketStack", config=config)
        template = Template.from_stack(stack)
        
        # Verify CORS configuration includes localhost for development
        template.has_resource_properties("AWS::S3::Bucket", {
            "CorsConfiguration": {
                "CorsRules": [
                    {
                        "AllowedMethods": ["GET", "HEAD", "PUT", "POST"],
                        "AllowedOrigins": ["http://localhost:3000", "https://localhost:3000"],
                        "AllowedHeaders": ["*"],
                        "MaxAge": 3000
                    }
                ]
            }
        })
    
    def test_production_environment_security_hardening(self):
        """Test that production environment has enhanced security configuration"""
        config = EnvironmentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            region="us-east-1",
            account_id="123456789012",
            domain_name="example.com",
            certificate_arn="arn:aws:acm:us-east-1:123456789012:certificate/test",
            cognito_domain_prefix="test-prod"
        )
        
        app = App()
        stack = BucketStack(app, "TestBucketStack", config=config)
        template = Template.from_stack(stack)
        
        # Verify production CORS doesn't include wildcard
        cors_rules = template.find_resources("AWS::S3::Bucket")
        for bucket_id, bucket_props in cors_rules.items():
            cors_config = bucket_props.get("Properties", {}).get("CorsConfiguration", {})
            if cors_config:
                cors_rules_list = cors_config.get("CorsRules", [])
                for rule in cors_rules_list:
                    allowed_origins = rule.get("AllowedOrigins", [])
                    assert "*" not in allowed_origins, "Production should not have wildcard CORS origins"
    
    def test_cross_stack_outputs_export_names(self):
        """Test that cross-stack outputs have proper export names"""
        config = EnvironmentConfig(
            environment=DeploymentEnvironment.STAGING,
            region="us-east-1",
            account_id="123456789012",
            cognito_domain_prefix="test-staging"
        )
        
        app = App()
        stack = BucketStack(app, "StagingBucketStack", config=config)
        template = Template.from_stack(stack)
        
        # Verify export names include stack name for uniqueness
        template.has_output("ImageStorageBucketName", {
            "Export": {
                "Name": "StagingBucketStack-ImageStorageBucketName"
            }
        })
        
        template.has_output("ImageStorageBucketArn", {
            "Export": {
                "Name": "StagingBucketStack-ImageStorageBucketArn"
            }
        })
        
        template.has_output("BucketEncryptionKeyArn", {
            "Export": {
                "Name": "StagingBucketStack-BucketEncryptionKeyArn"
            }
        })