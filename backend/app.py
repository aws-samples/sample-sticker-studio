#!/usr/bin/env python3
import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from config.environment import EnvironmentConfig
from stacks.bucketStack import BucketStack
from stacks.apiStack import ApiStack
from stacks.fargateStack import FargateStack
from stacks.cognitoStack import CognitoStack
from stacks.cloudfrontStack import CloudFrontStack
from stacks.nag_suppressions import apply_all_suppressions

app = cdk.App()
cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

# Load environment configuration
config = EnvironmentConfig.from_context(app)

# Create stacks with proper dependency order
# Foundation Layer: Independent infrastructure
bucket_stack = BucketStack(app, f"{config.resource_prefix}BucketStack", config=config)
cognito_stack = CognitoStack(app, f"{config.resource_prefix}CognitoStack", config=config)

# Application Layer: Depends on foundation
api_stack = ApiStack(
    app,
    f"{config.resource_prefix}ApiStack",
    bucket_stack=bucket_stack,
    cognito_stack=cognito_stack,
    config=config,
)

# Hosting Layer: Depends on application and foundation
fargate_stack = FargateStack(
    app, 
    f"{config.resource_prefix}FargateStack",
    cognito_stack=cognito_stack,
    api_stack=api_stack,
    config=config,
)

# Distribution Layer: Depends on hosting
cloudfront_stack = CloudFrontStack(
    app,
    f"{config.resource_prefix}CloudFrontStack",
    fargate_stack=fargate_stack,
    config=config,
)

# Apply all cdk-nag suppressions from a single location
apply_all_suppressions(
    bucket_stack=bucket_stack,
    cognito_stack=cognito_stack,
    api_stack=api_stack,
    fargate_stack=fargate_stack,
    cloudfront_stack=cloudfront_stack,
    config=config,
)

app.synth()
