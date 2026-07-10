"""
Environment Configuration System for AWS Sticker Studio

This module provides centralized configuration management for environment-specific
values, supporting deployment across different AWS accounts and regions.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from aws_cdk import App


class DeploymentEnvironment(Enum):
    """Supported deployment environments"""
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"


@dataclass
class SecurityConfig:
    """Security-related configuration settings"""
    cors_allowed_origins: Optional[list] = None
    
    def __post_init__(self):
        if self.cors_allowed_origins is None:
            self.cors_allowed_origins = []


@dataclass
class EnvironmentConfig:
    """
    Centralized environment configuration for CDK deployment.
    
    Loads configuration from environment variables and CDK context,
    with validation for required parameters.
    """
    environment: DeploymentEnvironment
    region: str
    account_id: str
    
    # Optional domain configuration
    domain_name: Optional[str] = None
    certificate_arn: Optional[str] = None
    
    # Cognito configuration

    # Set via CLOUDFRONT_DOMAIN env var or --context cloudfront_domain=... after first deploy.
    cloudfront_domain: Optional[str] = None

    cognito_domain_prefix: str = "sticker-studio"
    
    # Security settings
    security: SecurityConfig = None
    
    # Resource naming
    resource_prefix: str = "StickerStudio"
    
    # Bedrock configuration
    bedrock_region: str = "us-west-2"
    
    def __post_init__(self):
        """Initialize default configurations if not provided"""
        if self.security is None:
            self.security = SecurityConfig()
            
        # Adjust security settings based on environment
        if self.environment == DeploymentEnvironment.PRODUCTION:
            self.security.cors_allowed_origins = (
                [f"https://{self.domain_name}"]
                if self.domain_name
                else ["https://localhost:3000"]
            )
        elif self.environment == DeploymentEnvironment.STAGING:
            if self.cloudfront_domain:
                self.security.cors_allowed_origins = [
                    f"https://{self.cloudfront_domain}"
                ]
            else:
                self.security.cors_allowed_origins = ["https://localhost:3000"]
        elif self.environment == DeploymentEnvironment.DEVELOPMENT:
            allowed_origins = ["https://localhost:3000"]
            if self.cloudfront_domain:
                allowed_origins.append(f"https://{self.cloudfront_domain}")
            self.security.cors_allowed_origins = allowed_origins

    def get_resource_name(self, base_name: str) -> str:
        """Generate consistent resource names with environment prefix"""
        return f"{self.resource_prefix}-{base_name}-{self.environment.value}"
    
    def get_cognito_callback_urls(self) -> list:
        """Generate environment-appropriate Cognito callback URLs"""
        urls = []
        
        if self.environment == DeploymentEnvironment.DEVELOPMENT:
            urls.extend(
                [
                    "http://localhost:3000",
                    "https://localhost:3000",
                    "http://localhost:3000/auth/callback",
                    "https://localhost:3000/auth/callback",
                ]
            )

        if self.cloudfront_domain:
            urls.extend(
                [
                    f"https://{self.cloudfront_domain}",
                    f"https://{self.cloudfront_domain}/auth/callback",
                ]
            )

        if self.domain_name:
            urls.extend(
                [
                    f"https://{self.domain_name}",
                    f"https://{self.domain_name}/auth/callback",
                ]
            )

        # Fallback for initial deploy when no domains are known yet
        if not urls:
            urls.append("https://localhost:3000")

        return urls
    
    def validate(self) -> None:
        """
        Validate configuration parameters and raise descriptive errors
        for missing or invalid values.
        """
        from .region_utils import RegionAdapter, adapt_resources_for_region
        
        errors = []
        
        # Required parameters
        if not self.region:
            errors.append("Region is required (set AWS_DEFAULT_REGION or CDK_DEFAULT_REGION)")
        
        # Account ID is optional - CDK can resolve it dynamically
        # Only validate if explicitly provided
        if self.account_id and len(self.account_id) != 12:
            errors.append("Account ID must be 12 digits if provided")
        
        if not self.cognito_domain_prefix:
            errors.append("Cognito domain prefix is required (set COGNITO_DOMAIN_PREFIX)")
        
        # Environment-specific validation
        if self.environment == DeploymentEnvironment.PRODUCTION:
            if not self.domain_name:
                errors.append("Domain name is required for production environment (set DOMAIN_NAME)")
            if not self.certificate_arn:
                errors.append("Certificate ARN is required for production environment (set CERTIFICATE_ARN)")
        
        # Enhanced region validation using RegionAdapter
        if self.region:
            if not RegionAdapter.validate_region(self.region):
                supported_regions = RegionAdapter.get_supported_regions()
                errors.append(f"Region '{self.region}' is not supported. Supported regions: {supported_regions}")
            else:
                # Validate region constraints for the application
                requirements = {
                    "bedrock_required": True,
                    "fargate_required": True,
                    "min_availability_zones": 2,
                    "required_models": ["stability.stable-image-ultra-v1:1"]
                }
                
                region_errors = RegionAdapter.validate_region_constraints(self.region, requirements)
                if region_errors:
                    errors.extend([f"Region constraint: {error}" for error in region_errors])
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_message)
    
    def get_region_adapted_config(self) -> Dict[str, any]:
        """
        Get region-adapted configuration for deployment.
        
        Returns:
            Dictionary containing region-specific resource configurations
        """
        from .region_utils import adapt_resources_for_region
        return adapt_resources_for_region(self.region)
    
    @classmethod
    def from_context(cls, app: App) -> 'EnvironmentConfig':
        """
        Load configuration from CDK context and environment variables.
        
        Priority order:
        1. CDK context values (cdk.json or --context flags)
        2. Environment variables
        3. Default values
        """
        # Get environment from context or env var
        env_name = (
            app.node.try_get_context("environment") or 
            os.environ.get("ENVIRONMENT", "dev")
        )
        
        try:
            environment = DeploymentEnvironment(env_name)
        except ValueError:
            raise ValueError(f"Invalid environment '{env_name}'. Must be one of: {[e.value for e in DeploymentEnvironment]}")
        
        # Get region and account
        region = (
            app.node.try_get_context("region") or
            os.environ.get("CDK_DEFAULT_REGION") or
            os.environ.get("AWS_DEFAULT_REGION") or
            "us-east-1"
        )
        
        # Dynamic account resolution - let CDK resolve if not provided
        account_id = (
            app.node.try_get_context("account") or
            os.environ.get("CDK_DEFAULT_ACCOUNT") or
            ""  # Empty string allows CDK to resolve dynamically
        )
        
        # Get optional configuration
        domain_name = (
            app.node.try_get_context("domain_name") or
            os.environ.get("DOMAIN_NAME")
        )
        
        certificate_arn = (
            app.node.try_get_context("certificate_arn") or
            os.environ.get("CERTIFICATE_ARN")
        )

        # Only known after first CloudFront deploy; pass via CLOUDFRONT_DOMAIN or --context.
        cloudfront_domain = app.node.try_get_context(
            "cloudfront_domain"
        ) or os.environ.get("CLOUDFRONT_DOMAIN")

        cognito_domain_prefix = (
            app.node.try_get_context("cognito_domain_prefix") or
            os.environ.get("COGNITO_DOMAIN_PREFIX") or
            f"sticker-studio-{env_name}-{account_id[-6:]}" if account_id else f"sticker-studio-{env_name}"
        )

        resource_prefix = (
            app.node.try_get_context("resource_prefix") or
            os.environ.get("RESOURCE_PREFIX") or
            "StickerStudio"
        )

        bedrock_region = (
            app.node.try_get_context("bedrock_region") or
            os.environ.get("BEDROCK_REGION") or
            "us-west-2"
        )
        
        # Create configuration instance
        config = cls(
            environment=environment,
            region=region,
            account_id=account_id,
            domain_name=domain_name,
            certificate_arn=certificate_arn,
            cloudfront_domain=cloudfront_domain,
            cognito_domain_prefix=cognito_domain_prefix,
            resource_prefix=resource_prefix,
            bedrock_region=bedrock_region,
        )
        
        # Validate configuration
        config.validate()
        
        return config
    
    @classmethod
    def from_environment_variables(cls) -> 'EnvironmentConfig':
        """
        Load configuration directly from environment variables.
        Useful for testing and CI/CD environments.
        """
        env_name = os.environ.get("ENVIRONMENT", "dev")
        
        try:
            environment = DeploymentEnvironment(env_name)
        except ValueError:
            raise ValueError(f"Invalid environment '{env_name}'. Must be one of: {[e.value for e in DeploymentEnvironment]}")
        
        account_id = os.environ.get("CDK_DEFAULT_ACCOUNT", "")
        default_prefix = f"sticker-studio-{env_name}-{account_id[-6:]}" if account_id else f"sticker-studio-{env_name}"
        
        config = cls(
            environment=environment,
            region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            account_id=account_id,
            domain_name=os.environ.get("DOMAIN_NAME"),
            certificate_arn=os.environ.get("CERTIFICATE_ARN"),
            cloudfront_domain=os.environ.get("CLOUDFRONT_DOMAIN"),
            cognito_domain_prefix=os.environ.get(
                "COGNITO_DOMAIN_PREFIX", default_prefix
            ),
            resource_prefix=os.environ.get("RESOURCE_PREFIX", "StickerStudio"),
        )
        
        config.validate()
        return config


def get_region_specific_layer_arn(region: str, layer_name: str) -> Optional[str]:
    """Get region-specific Lambda layer ARN. Delegates to RegionAdapter."""
    from .region_utils import RegionAdapter

    return RegionAdapter.get_lambda_layer_arn(region, layer_name)
