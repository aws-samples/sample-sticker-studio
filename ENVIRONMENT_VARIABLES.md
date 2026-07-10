# Environment Variables Reference

This document provides a comprehensive reference for all environment variables used by AWS Sticker Studio deployment system.

## Quick Reference

### Minimal Development Setup
```bash
export ENVIRONMENT=dev
export AWS_DEFAULT_REGION=us-east-1
./deploy-project.sh --environment dev
```

### Production Setup
```bash
export ENVIRONMENT=prod
export AWS_DEFAULT_REGION=us-east-1
export DOMAIN_NAME=stickers.example.com
export CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789012:certificate/...
export COGNITO_DOMAIN_PREFIX=sticker-studio-prod
./deploy-project.sh --environment prod
```

## Core Configuration Variables

### ENVIRONMENT
- **Required**: Yes
- **Values**: `dev`, `staging`, `prod`
- **Description**: Deployment environment that determines security settings, monitoring level, and resource configuration
- **Example**: `export ENVIRONMENT=dev`

### AWS_DEFAULT_REGION
- **Required**: Yes
- **Values**: Any valid AWS region
- **Description**: AWS region for deployment. Must support Bedrock, ECS Fargate, and other required services
- **Example**: `export AWS_DEFAULT_REGION=us-east-1`
- **Supported Regions**: `us-east-1`, `us-west-2`, `eu-west-1`, `ap-southeast-1`, etc.

### BEDROCK_REGION
- **Required**: No
- **Default**: `us-west-2`
- **Description**: AWS region where Amazon Bedrock is called for image generation. This can differ from the deployment region if the desired model is not available in the deployment region.
- **Example**: `export BEDROCK_REGION=us-west-2`
- **Notes**:
  - The Stability AI Ultra model may not be available in all regions
  - Defaults to `us-west-2` which has broad model availability
  - Can also be set via CDK context: `--context bedrock_region=us-west-2`

## Domain and SSL Configuration

### DOMAIN_NAME
- **Required**: Yes for production, optional for dev/staging
- **Description**: Custom domain name for the application
- **Example**: `export DOMAIN_NAME=stickers.example.com`
- **Notes**: 
  - Must have valid DNS configuration
  - Required for production environment
  - Used for Cognito callback URLs and CORS configuration

### CERTIFICATE_ARN
- **Required**: Yes for production, optional for dev/staging
- **Description**: AWS Certificate Manager ARN for SSL certificate
- **Example**: `export CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012`
- **Notes**:
  - Certificate must be in the same region as deployment
  - Must cover the domain specified in DOMAIN_NAME
  - Required for production HTTPS enforcement

## Resource Configuration

### RESOURCE_PREFIX
- **Required**: No
- **Default**: `StickerStudio`
- **Description**: Prefix for all AWS resource names
- **Example**: `export RESOURCE_PREFIX=MyCompanyStickers`
- **Notes**: Use different prefixes to avoid naming conflicts between deployments

### COGNITO_DOMAIN_PREFIX
- **Required**: No
- **Default**: `sticker-studio-{environment}`
- **Description**: Prefix for Cognito user pool domain
- **Example**: `export COGNITO_DOMAIN_PREFIX=my-app-dev`
- **Notes**: Must be globally unique across all AWS accounts

## AWS Account and Credentials

### CDK_DEFAULT_ACCOUNT
- **Required**: No (auto-detected)
- **Description**: AWS account ID for deployment
- **Example**: `export CDK_DEFAULT_ACCOUNT=123456789012`
- **Notes**: CDK will auto-detect if not provided using AWS STS

### CDK_DEFAULT_REGION
- **Required**: No
- **Description**: Alternative way to specify AWS region
- **Example**: `export CDK_DEFAULT_REGION=us-east-1`
- **Notes**: AWS_DEFAULT_REGION takes precedence if both are set

## Deployment Control

## Deployment Control

### DRY_RUN
- **Required**: No
- **Default**: `false`
- **Values**: `true`, `false`
- **Description**: Show what would be deployed without making changes
- **Example**: `export DRY_RUN=true`
- **Use Cases**:
  - Validation before actual deployment
  - CI/CD pipeline testing
  - Configuration verification

## Monitoring and Logging

> **Note:** The following monitoring variables (`LOG_RETENTION_DAYS`, `ENABLE_DETAILED_MONITORING`, `ENABLE_XRAY`) are reserved for future implementation. They are not currently read by the CDK stacks. WAF and Shield are also not currently deployed (suppressed for this demo application).

### LOG_RETENTION_DAYS
- **Required**: No
- **Default**: `30` (dev), `90` (staging), `365` (prod)
- **Description**: CloudWatch log retention period in days
- **Example**: `export LOG_RETENTION_DAYS=90`
- **Valid Values**: `1`, `3`, `5`, `7`, `14`, `30`, `60`, `90`, `120`, `150`, `180`, `365`, `400`, `545`, `731`, `1827`, `3653`

### ENABLE_DETAILED_MONITORING
- **Required**: No
- **Default**: `false` (dev), `true` (prod)
- **Values**: `true`, `false`
- **Description**: Enable detailed CloudWatch monitoring
- **Example**: `export ENABLE_DETAILED_MONITORING=true`
- **Notes**: Increases monitoring costs but provides better insights

### ENABLE_XRAY
- **Required**: No
- **Default**: `true`
- **Values**: `true`, `false`
- **Description**: Enable AWS X-Ray distributed tracing
- **Example**: `export ENABLE_XRAY=false`
- **Notes**: Helps with performance analysis and debugging

## Debug and Development

### CDK_DEBUG
- **Required**: No
- **Default**: `false`
- **Values**: `true`, `false`
- **Description**: Enable CDK debug logging
- **Example**: `export CDK_DEBUG=true`
- **Use Cases**: Troubleshooting CDK synthesis and deployment issues

### DEBUG
- **Required**: No
- **Default**: `false`
- **Values**: `true`, `false`
- **Description**: Enable debug logging in deployment script
- **Example**: `export DEBUG=true`
- **Use Cases**: Troubleshooting deployment script issues

## Environment-Specific Defaults

### Development Environment (`ENVIRONMENT=dev`)
```bash
# Minimal required
ENVIRONMENT=dev
AWS_DEFAULT_REGION=us-east-1

# Automatic defaults
RESOURCE_PREFIX=StickerStudio
COGNITO_DOMAIN_PREFIX=sticker-studio-dev
LOG_RETENTION_DAYS=30
ENABLE_DETAILED_MONITORING=false
ENABLE_XRAY=true

# Behavior
# - Uses localhost URLs for Cognito callbacks
# - CORS allows localhost origins
# - Basic security settings
# - Standard monitoring
```

### Staging Environment (`ENVIRONMENT=staging`)
```bash
# Required
ENVIRONMENT=staging
AWS_DEFAULT_REGION=us-east-1

# Optional but recommended
DOMAIN_NAME=staging-stickers.example.com
CERTIFICATE_ARN=arn:aws:acm:...

# Automatic defaults
RESOURCE_PREFIX=StickerStudio
COGNITO_DOMAIN_PREFIX=sticker-studio-staging
LOG_RETENTION_DAYS=90
ENABLE_DETAILED_MONITORING=true
ENABLE_XRAY=true

# Behavior
# - Can use custom domain
# - Enhanced monitoring
# - Production-like security
```

### Production Environment (`ENVIRONMENT=prod`)
```bash
# Required
ENVIRONMENT=prod
AWS_DEFAULT_REGION=us-east-1
DOMAIN_NAME=stickers.example.com
CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789012:certificate/...

# Recommended
COGNITO_DOMAIN_PREFIX=sticker-studio-prod

# Automatic defaults
RESOURCE_PREFIX=StickerStudio
LOG_RETENTION_DAYS=365
ENABLE_DETAILED_MONITORING=true
ENABLE_XRAY=true

# Automatic security features
# - Strict CORS policies
# - Enhanced encryption
# - WAF/Shield not currently deployed (reserved for future implementation)
```

## Configuration Loading Priority

The system loads configuration in this priority order:

1. **CDK Context** (highest priority)
   ```bash
   cdk deploy --context environment=prod --context domain_name=example.com
   ```

2. **Environment Variables**
   ```bash
   export ENVIRONMENT=prod
   export DOMAIN_NAME=example.com
   ```

3. **Default Values** (lowest priority)
   - Built-in defaults in the configuration system

## Validation Rules

The configuration system validates:

### Environment Value
- Must be one of: `dev`, `staging`, `prod`
- Case-sensitive

### Region Validation
- Must be a valid AWS region
- Must support required services (Bedrock, ECS, etc.)
- Automatically checks service availability

### Production Requirements
- `DOMAIN_NAME` is required
- `CERTIFICATE_ARN` is required
- Certificate must be valid for the domain

### Resource Naming
- Resource names must follow AWS naming conventions
- Prefixes must be valid for all resource types
- No conflicts with existing resources

## Common Patterns

### Multi-Environment Setup
```bash
# Development
export ENVIRONMENT=dev
export AWS_DEFAULT_REGION=us-east-1
./deploy-project.sh --environment dev

# Staging
export ENVIRONMENT=staging
export AWS_DEFAULT_REGION=us-east-1
export DOMAIN_NAME=staging.example.com
export CERTIFICATE_ARN=arn:aws:acm:...
./deploy-project.sh --environment staging

# Production
export ENVIRONMENT=prod
export AWS_DEFAULT_REGION=us-east-1
export DOMAIN_NAME=example.com
export CERTIFICATE_ARN=arn:aws:acm:...
./deploy-project.sh --environment prod
```

### Multi-Region Deployment
```bash
# US East
export AWS_DEFAULT_REGION=us-east-1
./deploy-project.sh --environment prod --region us-east-1

# Europe
export AWS_DEFAULT_REGION=eu-west-1
./deploy-project.sh --environment prod --region eu-west-1
```

### CI/CD Integration
```bash
# Set environment-specific variables
if [ "$CI_ENVIRONMENT" = "production" ]; then
  export ENVIRONMENT=prod
  export DOMAIN_NAME=$PROD_DOMAIN
  export CERTIFICATE_ARN=$PROD_CERT_ARN
else
  export ENVIRONMENT=dev
fi

# Deploy
./deploy-project.sh --environment $ENVIRONMENT
```

## Troubleshooting

### Configuration Validation Errors

**Error**: `Invalid environment 'development'`
```bash
# Fix: Use correct environment value
export ENVIRONMENT=dev  # not 'development'
```

**Error**: `Domain name is required for production`
```bash
# Fix: Set required production variables
export DOMAIN_NAME=stickers.example.com
export CERTIFICATE_ARN=arn:aws:acm:...
```

**Error**: `Region 'us-gov-east-1' is not supported`
```bash
# Fix: Use commercial AWS region
export AWS_DEFAULT_REGION=us-east-1
```

### Testing Configuration
```bash
# Test configuration loading
cd backend
python -c "
from config.environment import EnvironmentConfig
from aws_cdk import App
app = App()
try:
    config = EnvironmentConfig.from_context(app)
    print('✓ Configuration valid')
    print(f'Environment: {config.environment.value}')
    print(f'Region: {config.region}')
    print(f'Domain: {config.domain_name or \"None\"}')
except Exception as e:
    print(f'✗ Configuration error: {e}')
"
```

## Security Best Practices

1. **Never commit sensitive values**: Use environment variables or secrets management
2. **Use different accounts**: Separate AWS accounts for different environments
3. **Rotate certificates**: Keep SSL certificates current
4. **Limit access**: Restrict who can set production environment variables
5. **Audit configuration**: Log configuration changes
6. **Validate inputs**: Always validate configuration before deployment

## Integration Examples

### Docker Compose
```yaml
version: '3.8'
services:
  deploy:
    image: aws-cdk:latest
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-dev}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
      - DOMAIN_NAME=${DOMAIN_NAME}
      - CERTIFICATE_ARN=${CERTIFICATE_ARN}
    volumes:
      - .:/app
    working_dir: /app
    command: ./deploy-project.sh --environment ${ENVIRONMENT:-dev}
```

### Kubernetes ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sticker-studio-config
data:
  ENVIRONMENT: "prod"
  AWS_DEFAULT_REGION: "us-east-1"
  RESOURCE_PREFIX: "StickerStudio"
  LOG_RETENTION_DAYS: "365"
  ENABLE_DETAILED_MONITORING: "true"
```

### Terraform Integration
```hcl
variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

resource "null_resource" "deploy_sticker_studio" {
  provisioner "local-exec" {
    command = "./deploy-project.sh --environment ${var.environment}"
    environment = {
      ENVIRONMENT         = var.environment
      AWS_DEFAULT_REGION  = var.aws_region
      DOMAIN_NAME         = var.domain_name
      CERTIFICATE_ARN     = var.certificate_arn
    }
  }
}
```