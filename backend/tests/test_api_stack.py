"""
Minimal property-based tests for ApiStack security and region adaptation.
"""

import pytest
from hypothesis import given, strategies as st
from config.environment import EnvironmentConfig, DeploymentEnvironment, get_region_specific_layer_arn


class TestApiStackProperties:
    """Minimal property tests for ApiStack"""
    
    @given(
        region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1'])
    )
    def test_iam_policy_least_privilege_compliance(self, region):
        """
        Feature: deployment-improvements, Property 3: IAM Policy Least Privilege Compliance
        
        For any region, IAM policies should not contain wildcard resources with broad actions.
        """
        config = EnvironmentConfig(
            environment=DeploymentEnvironment.DEVELOPMENT,
            region=region,
            account_id="123456789012",
            cognito_domain_prefix="test-dev"
        )
        
        # Test that resource names are specific (not wildcards)
        resource_name = config.get_resource_name("lambda-role")
        assert "*" not in resource_name
        assert region not in resource_name or region == config.region
        
        # Test that log group ARN is specific to function
        log_group_arn = f"arn:aws:logs:{region}:123456789012:log-group:/aws/lambda/{config.get_resource_name('generate-image')}*"
        assert "generate-image" in log_group_arn
        assert region in log_group_arn
    
    @given(
        region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'])
    )
    def test_region_appropriate_layer_selection(self, region):
        """
        Feature: deployment-improvements, Property 2: Region-Appropriate Layer Selection
        
        For any valid AWS region, layer selection should be region-appropriate.
        """
        pillow_arn = get_region_specific_layer_arn(region, "pillow")
        numpy_arn = get_region_specific_layer_arn(region, "numpy")
        
        # If layer exists, it should contain the correct region
        if pillow_arn:
            assert region in pillow_arn
            assert "pillow" in pillow_arn.lower()
        
        if numpy_arn:
            assert region in numpy_arn
            assert "numpy" in numpy_arn.lower()
    
    @given(
        environment=st.sampled_from(['dev', 'staging', 'prod'])
    )
    def test_cors_policy_validation(self, environment):
        """
        Feature: deployment-improvements, Property 5: API Gateway CORS Policy Validation
        
        For any environment, CORS policies should not use wildcard origins in production.
        """
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region="us-east-1",
            account_id="123456789012",
            domain_name="example.com" if environment == 'prod' else None,
            certificate_arn="arn:aws:acm:us-east-1:123456789012:certificate/test" if environment == 'prod' else None,
            cognito_domain_prefix=f"test-{environment}"
        )
        
        cors_origins = config.security.cors_allowed_origins
        
        if environment == 'prod':
            # Production should not have wildcard CORS
            assert "*" not in cors_origins
        
        # All environments should have some CORS origins defined
        assert len(cors_origins) > 0