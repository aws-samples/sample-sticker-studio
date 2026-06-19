"""
Minimal property-based tests for CognitoStack URL generation.
"""

import pytest
from hypothesis import given, strategies as st
from config.environment import EnvironmentConfig, DeploymentEnvironment


class TestCognitoStackProperties:
    """Minimal property tests for Cognito URL generation"""
    
    @given(
        environment=st.sampled_from(['dev', 'staging']),  # Focus on dev/staging for simplicity
        domain=st.one_of(st.none(), st.just("example.com"))  # Simple domain or none
    )
    def test_cognito_url_generation_consistency(self, environment, domain):
        """
        Feature: deployment-improvements, Property 1: Cognito URL Generation Consistency
        
        For any environment configuration, callback URLs should follow the correct pattern.
        """
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region="us-east-1",
            account_id="123456789012",
            domain_name=domain,
            cognito_domain_prefix=f"test-{environment}"
        )
        
        callback_urls = config.get_cognito_callback_urls()
        
        # Verify URLs are generated
        assert len(callback_urls) > 0
        
        # Verify environment-specific patterns
        if environment == 'dev':
            assert any('localhost' in url for url in callback_urls)
        elif domain:
            assert any(domain in url for url in callback_urls)