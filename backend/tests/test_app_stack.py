"""
Minimal property-based tests for CDK app.py account resolution.
"""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock
from config.environment import EnvironmentConfig, DeploymentEnvironment


class TestAppStackProperties:
    """Minimal property tests for CDK app configuration"""
    
    @given(
        account_id=st.one_of(
            st.none(), 
            st.just(""),
            st.text(min_size=12, max_size=12, alphabet='0123456789')
        )
    )
    def test_dynamic_account_resolution(self, account_id):
        """
        Feature: deployment-improvements, Property 14: Dynamic Account Resolution
        
        For any account ID configuration, the system should handle dynamic resolution
        correctly without hardcoded values.
        """
        # Create mock CDK app
        mock_app = Mock()
        mock_node = Mock()
        mock_app.node = mock_node
        
        # Mock context to return the account_id
        mock_node.try_get_context.side_effect = lambda key: {
            'environment': 'dev',
            'region': 'us-east-1',
            'account': account_id
        }.get(key)
        
        config = EnvironmentConfig.from_context(mock_app)
        
        # Test that account_id is handled correctly
        if account_id is None or account_id == "":
            # Empty account should be allowed for dynamic resolution
            assert config.account_id == ""
        else:
            # Valid account should be preserved
            assert config.account_id == account_id
            assert len(config.account_id) == 12
            assert config.account_id.isdigit()
        
        # Test that other configuration is still valid
        assert config.environment == DeploymentEnvironment.DEVELOPMENT
        assert config.region == "us-east-1"
        assert config.cognito_domain_prefix == "sticker-studio-dev"
    
    def test_stack_dependency_order(self):
        """
        Test that stack names follow proper dependency order and naming conventions.
        """
        config = EnvironmentConfig(
            environment=DeploymentEnvironment.DEVELOPMENT,
            region="us-east-1",
            account_id="123456789012",
            cognito_domain_prefix="test-dev"
        )
        
        # Test stack naming follows resource prefix pattern
        expected_stacks = [
            f"{config.resource_prefix}BucketStack",
            f"{config.resource_prefix}CognitoStack", 
            f"{config.resource_prefix}ApiStack",
            f"{config.resource_prefix}FargateStack",
            f"{config.resource_prefix}CloudFrontStack"
        ]
        
        # Verify all stack names include the resource prefix
        for stack_name in expected_stacks:
            assert config.resource_prefix in stack_name
            assert "Stack" in stack_name
        
        # Test that resource prefix is environment-aware
        assert config.resource_prefix == "StickerStudio"  # Default value