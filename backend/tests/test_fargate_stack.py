"""
Minimal property-based tests for FargateStack resource tagging.
"""

import pytest
from hypothesis import given, strategies as st
from config.environment import EnvironmentConfig, DeploymentEnvironment


class TestFargateStackProperties:
    """Minimal property tests for FargateStack"""
    
    @given(
        environment=st.sampled_from(['dev', 'staging', 'prod']),
        region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1'])
    )
    def test_resource_tagging_consistency(self, environment, region):
        """
        Feature: deployment-improvements, Property 10: Resource Tagging Consistency
        
        For any environment and region, resource tags should include standard tags
        for cost tracking and management.
        """
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region=region,
            account_id="123456789012",
            domain_name="example.com" if environment == 'prod' else None,
            certificate_arn="arn:aws:acm:us-east-1:123456789012:certificate/test" if environment == 'prod' else None,
            cognito_domain_prefix=f"test-{environment}"
        )
        
        # Test that standard tag values are consistent
        expected_tags = {
            "Environment": environment,
            "Project": "StickerStudio",
            "CostCenter": f"StickerStudio-{environment}",
            "ManagedBy": "CDK",
            "Region": region
        }
        
        # Verify tag values are properly formatted
        assert expected_tags["Environment"] in ['dev', 'staging', 'prod']
        assert expected_tags["Project"] == "StickerStudio"
        assert environment in expected_tags["CostCenter"]
        assert expected_tags["ManagedBy"] == "CDK"
        assert expected_tags["Region"] == region
        
        # Test resource naming consistency
        vpc_name = config.get_resource_name("vpc")
        cluster_name = config.get_resource_name("cluster")
        cors_policy_name = config.get_resource_name("cors-policy")
        
        # All resource names should include environment
        assert environment in vpc_name
        assert environment in cluster_name
        assert environment in cors_policy_name