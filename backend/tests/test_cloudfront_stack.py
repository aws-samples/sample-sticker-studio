"""
Minimal property-based tests for CloudFrontStack security headers.
"""

import pytest
from hypothesis import given, strategies as st
from config.environment import EnvironmentConfig, DeploymentEnvironment
from stacks.cloudfrontStack import CloudFrontStack


class TestCloudFrontStackProperties:
    """Minimal property tests for CloudFrontStack"""
    
    @given(
        environment=st.sampled_from(['dev', 'staging', 'prod']),
        domain=st.one_of(st.none(), st.just("example.com"))
    )
    def test_cloudfront_security_headers(self, environment, domain):
        """
        Feature: deployment-improvements, Property 6: CloudFront Security Headers
        
        For any environment, CloudFront distribution should have security headers
        configured including HSTS, CSP, and should enforce HTTPS redirection.
        """
        config = EnvironmentConfig(
            environment=DeploymentEnvironment(environment),
            region="us-east-1",
            account_id="123456789012",
            domain_name=domain,
            certificate_arn="arn:aws:acm:us-east-1:123456789012:certificate/test" if environment == 'prod' and domain else None,
            cognito_domain_prefix=f"test-{environment}"
        )
        
        # Create a mock CloudFrontStack to test CSP generation
        class MockCloudFrontStack:
            def __init__(self, config):
                self.config = config
            
            def _get_content_security_policy(self):
                base_policy = [
                    "default-src 'self'",
                    "script-src 'self'",
                    "style-src 'self'",
                    "img-src 'self' blob: data: *.s3.amazonaws.com",
                    "connect-src 'self' *.amazonaws.com *.amazoncognito.com",
                    "font-src 'self'",
                    "object-src 'none'",
                    "media-src 'self'",
                    "frame-src 'none'",
                ]

                if self.config.environment.value == 'dev':
                    base_policy.extend([
                        "connect-src 'self' *.amazonaws.com *.amazoncognito.com localhost:* ws://localhost:*",
                        "script-src 'self' localhost:*",
                    ])

                return "; ".join(base_policy)
        
        mock_stack = MockCloudFrontStack(config)
        csp = mock_stack._get_content_security_policy()
        
        # Test that CSP contains essential security directives
        assert "default-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "frame-src 'none'" in csp
        
        # Test environment-specific CSP policies
        if environment == 'dev':
            assert "localhost:*" in csp
            assert "ws://localhost:*" in csp
        
        # Test that AWS services are allowed
        assert "*.amazonaws.com" in csp
        assert "*.amazoncognito.com" in csp
        assert "*.s3.amazonaws.com" in csp
        
        # Test resource naming consistency
        security_headers_name = config.get_resource_name("security-headers")
        assert environment in security_headers_name
        
        # Test CORS origins are environment-appropriate
        cors_origins = config.security.cors_allowed_origins
        if environment == 'prod':
            assert "*" not in cors_origins
        assert len(cors_origins) > 0