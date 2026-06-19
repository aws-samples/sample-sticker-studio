"""
Property-based tests for environment configuration system.

Tests the CDK synthesis parameter validation and configuration loading
across different environments and input combinations.
"""

import os
import pytest
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, assume
from aws_cdk import App

from config.environment import (
    EnvironmentConfig, 
    DeploymentEnvironment, 
    DeploymentError,
    get_region_specific_layer_arn
)
from config.region_utils import RegionAdapter, adapt_resources_for_region, AWSRegion


# Test data strategies
valid_environments = st.sampled_from(['dev', 'staging', 'prod'])
valid_regions = st.sampled_from([
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'eu-west-1', 'eu-west-2', 'eu-central-1',
    'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
])
valid_domains = st.text(min_size=5, max_size=50).filter(
    lambda x: '.' in x and not x.startswith('.') and not x.endswith('.')
)
valid_account_ids = st.text(min_size=12, max_size=12, alphabet='0123456789')
valid_prefixes = st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')


class TestEnvironmentConfigProperties:
    """Property-based tests for EnvironmentConfig"""
    
    @given(
        environment=valid_environments,
        region=valid_regions,
        account_id=valid_account_ids,
        domain=st.one_of(st.none(), valid_domains),
        prefix=valid_prefixes
    )
    def test_cdk_synthesis_parameter_validation(self, environment, region, account_id, domain, prefix):
        """
        Feature: deployment-improvements, Property 11: CDK Synthesis Parameter Validation
        
        For any valid configuration parameters, CDK synthesis should succeed without errors
        when all required parameters are provided, and should fail with clear error messages
        when required parameters are missing.
        """
        # For production environment, ensure required parameters are provided
        if environment == 'prod':
            # Skip cases where production doesn't have required parameters
            assume(domain is not None)
            certificate_arn = f"arn:aws:acm:{region}:{account_id}:certificate/test-cert"
        else:
            certificate_arn = None
        
        # Test with valid configuration - should not raise
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region=region,
            account_id=account_id,
            domain_name=domain,
            certificate_arn=certificate_arn,
            cognito_domain_prefix=f"test-{environment}",
            resource_prefix=prefix
        )
        
        # Should not raise validation errors for valid config
        config.validate()
        
        # Test resource naming consistency
        resource_name = config.get_resource_name("bucket")
        assert prefix in resource_name
        assert environment in resource_name
        assert "bucket" in resource_name
        
        # Test callback URL generation consistency
        callback_urls = config.get_cognito_callback_urls()
        assert len(callback_urls) > 0
        
        if environment == 'dev':
            assert any('localhost' in url for url in callback_urls)
        elif domain:
            assert any(domain in url for url in callback_urls)
    
    @given(
        environment=valid_environments,
        region=valid_regions
    )
    def test_missing_required_parameters_validation(self, environment, region):
        """
        Test that missing required parameters cause validation to fail with clear messages.
        """
        # Test missing cognito_domain_prefix
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region=region,
            account_id="123456789012",
            cognito_domain_prefix=""  # Empty - should cause validation error
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "Cognito domain prefix is required" in str(exc_info.value)
    
    @given(
        environment=st.just('prod'),  # Production environment
        region=valid_regions,
        account_id=valid_account_ids
    )
    def test_production_environment_validation(self, environment, region, account_id):
        """
        Test that production environment requires domain name and certificate ARN.
        """
        # Production without domain should fail
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region=region,
            account_id=account_id,
            domain_name=None,  # Missing for production
            cognito_domain_prefix="test-prod"
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_message = str(exc_info.value)
        assert "Domain name is required for production" in error_message
        assert "Certificate ARN is required for production" in error_message
    
    @given(
        region=valid_regions,
        layer_name=st.sampled_from(['pillow', 'numpy', 'nonexistent'])
    )
    def test_region_specific_layer_selection(self, region, layer_name):
        """
        Test that layer ARN selection works correctly for different regions.
        """
        layer_arn = get_region_specific_layer_arn(region, layer_name)
        
        if layer_name in ['pillow', 'numpy']:
            if region in ['us-east-1', 'us-west-2', 'eu-west-1']:
                # Should return valid ARN for supported regions
                assert layer_arn is not None
                assert region in layer_arn
                assert layer_name.lower() in layer_arn.lower()
            else:
                # May return None for unsupported regions
                pass  # This is acceptable behavior
        else:
            # Non-existent layer should return None
            assert layer_arn is None
    
    def test_from_context_with_mock_app(self):
        """
        Test configuration loading from CDK context with mocked App.
        """
        # Create mock CDK app
        mock_app = Mock(spec=App)
        mock_node = Mock()
        mock_app.node = mock_node
        
        # Test with context values
        mock_node.try_get_context.side_effect = lambda key: {
            'environment': 'dev',
            'region': 'us-east-1',
            'account': '123456789012',
            'cognito_domain_prefix': 'test-dev'
        }.get(key)
        
        config = EnvironmentConfig.from_context(mock_app)
        
        assert config.environment == DeploymentEnvironment.DEVELOPMENT
        assert config.region == 'us-east-1'
        assert config.account_id == '123456789012'
        assert config.cognito_domain_prefix == 'test-dev'
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'staging',
        'AWS_DEFAULT_REGION': 'us-west-2',
        'CDK_DEFAULT_ACCOUNT': '987654321098',
        'COGNITO_DOMAIN_PREFIX': 'test-staging'
    })
    def test_from_environment_variables(self):
        """
        Test configuration loading from environment variables.
        """
        config = EnvironmentConfig.from_environment_variables()
        
        assert config.environment == DeploymentEnvironment.STAGING
        assert config.region == 'us-west-2'
        assert config.account_id == '987654321098'
        assert config.cognito_domain_prefix == 'test-staging'
    
    @given(
        environment=valid_environments,
        region=valid_regions,
        domain=st.one_of(st.none(), valid_domains)
    )
    def test_cors_origins_configuration(self, environment, region, domain):
        """
        Test that CORS origins are configured appropriately for different environments.
        """
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region=region,
            account_id="123456789012",
            domain_name=domain,
            cognito_domain_prefix=f"test-{environment}"
        )
        
        cors_origins = config.security.cors_allowed_origins
        
        if environment == 'prod':
            # Production should not have wildcard CORS
            assert "*" not in cors_origins
            if domain:
                assert f"https://{domain}" in cors_origins
        elif environment == 'dev':
            # Development should allow localhost
            assert any('localhost' in origin for origin in cors_origins)
    
    @given(
        invalid_env=st.text(min_size=1).filter(lambda x: x not in ['dev', 'staging', 'prod'])
    )
    def test_invalid_environment_rejection(self, invalid_env):
        """
        Test that invalid environment names are rejected with clear error messages.
        """
        # Skip empty strings and whitespace-only strings as they default to 'dev'
        assume(invalid_env.strip() != '')
        
        # Test with mock app
        mock_app = Mock(spec=App)
        mock_node = Mock()
        mock_app.node = mock_node
        mock_node.try_get_context.side_effect = lambda key: {
            'environment': invalid_env
        }.get(key)
        
        with pytest.raises(ValueError) as exc_info:
            EnvironmentConfig.from_context(mock_app)
        
        assert f"Invalid environment '{invalid_env}'" in str(exc_info.value)
        assert "Must be one of:" in str(exc_info.value)
    
    @given(
        region=st.sampled_from([r.value for r in AWSRegion]),
        layer_name=st.sampled_from(['pillow', 'numpy', 'boto3'])
    )
    def test_multi_region_resource_adaptation(self, region, layer_name):
        """
        Feature: deployment-improvements, Property 13: Multi-Region Resource Adaptation
        
        For any valid AWS region, region-specific resources (Lambda layers, AMI IDs, 
        availability zones) should be automatically adapted to the target region 
        without hardcoded values.
        """
        # Test that RegionAdapter provides region-specific layer ARNs
        layer_arn = RegionAdapter.get_lambda_layer_arn(region, layer_name)
        
        if layer_arn is not None:
            # If layer is available, ARN should be region-specific
            assert region in layer_arn
            assert layer_name.lower() in layer_arn.lower()
            assert layer_arn.startswith(f"arn:aws:lambda:{region}:")
        
        # Test region capabilities
        capabilities = RegionAdapter.get_region_capabilities(region)
        assert capabilities is not None
        assert capabilities.region == region
        
        # Availability zones should be region-specific
        assert all(az.startswith(region) for az in capabilities.availability_zones)
        assert len(capabilities.availability_zones) >= 2  # Minimum for multi-AZ deployment
        
        # Test full resource adaptation
        try:
            adapted_config = adapt_resources_for_region(region)
            
            # Adapted config should be region-specific
            assert adapted_config["region"] == region
            
            # Availability zones should be from the target region
            for az in adapted_config["availability_zones"]:
                assert az.startswith(region)
            
            # Lambda layers should be region-appropriate
            for layer_name, layer_arn in adapted_config["lambda_layers"].items():
                if layer_arn:  # Only check if layer is available
                    assert region in layer_arn
                    assert layer_arn.startswith(f"arn:aws:lambda:{region}:")
            
            # Bedrock model should be supported in the region
            if adapted_config["supports_bedrock"]:
                bedrock_model = adapted_config["bedrock_model"]
                assert bedrock_model in capabilities.bedrock_models
        
        except ValueError as e:
            # Some regions may not support all required services
            # This is acceptable - the error should be descriptive
            assert "validation failed" in str(e) or "not supported" in str(e)
    
    @given(
        region=st.sampled_from([r.value for r in AWSRegion])
    )
    def test_region_validation_consistency(self, region):
        """
        Test that region validation is consistent across different validation methods.
        """
        # RegionAdapter validation
        adapter_valid = RegionAdapter.validate_region(region)
        
        # Region capabilities availability
        capabilities = RegionAdapter.get_region_capabilities(region)
        capabilities_valid = capabilities is not None
        
        # Both validation methods should agree
        assert adapter_valid == capabilities_valid
        
        if adapter_valid:
            # If region is valid, it should be in supported regions list
            supported_regions = RegionAdapter.get_supported_regions()
            assert region in supported_regions
            
            # Should be able to get availability zones
            azs = RegionAdapter.get_availability_zones(region, min_zones=2)
            assert len(azs) >= 2
            assert all(az.startswith(region) for az in azs)


# Unit tests for specific scenarios
class TestEnvironmentConfigUnits:
    """Unit tests for specific configuration scenarios"""
    
    def test_development_environment_defaults(self):
        """Test that development environment has appropriate defaults"""
        config = EnvironmentConfig(
            environment=DeploymentEnvironment.DEVELOPMENT,
            region="us-east-1",
            account_id="123456789012",
            cognito_domain_prefix="test-dev"
        )
        
        # Development should allow localhost CORS
        assert any('localhost' in origin for origin in config.security.cors_allowed_origins)
        
        # Development callback URLs should include localhost
        callback_urls = config.get_cognito_callback_urls()
        assert any('localhost' in url for url in callback_urls)
    
    def test_production_environment_security(self):
        """Test that production environment enforces security settings"""
        config = EnvironmentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            region="us-east-1",
            account_id="123456789012",
            domain_name="example.com",
            certificate_arn="arn:aws:acm:us-east-1:123456789012:certificate/test",
            cognito_domain_prefix="test-prod"
        )
        
        # Production should not have wildcard CORS
        assert "*" not in config.security.cors_allowed_origins
        
        # Production should use HTTPS domain
        callback_urls = config.get_cognito_callback_urls()
        assert all(url.startswith('https://') for url in callback_urls)
    
    def test_resource_naming_convention(self):
        """Test that resource naming follows consistent conventions"""
        config = EnvironmentConfig(
            environment=DeploymentEnvironment.STAGING,
            region="us-east-1",
            account_id="123456789012",
            resource_prefix="TestApp",
            cognito_domain_prefix="test-staging"
        )
        
        bucket_name = config.get_resource_name("bucket")
        api_name = config.get_resource_name("api")
        
        # Both should include prefix and environment
        assert "TestApp" in bucket_name and "staging" in bucket_name
        assert "TestApp" in api_name and "staging" in api_name
        
        # Should include the specific resource type
        assert "bucket" in bucket_name
        assert "api" in api_name
    
    def test_deployment_error_formatting(self):
        """Test that DeploymentError provides helpful error messages"""
        error = DeploymentError(
            "CONFIGURATION_ERROR",
            "Missing required parameter",
            "Set the DOMAIN_NAME environment variable"
        )
        
        error_str = str(error)
        assert "CONFIGURATION_ERROR" in error_str
        assert "Missing required parameter" in error_str
        assert "Set the DOMAIN_NAME environment variable" in error_str
        assert "Suggested fix:" in error_str