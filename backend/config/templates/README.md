# Environment Configuration Templates

This directory contains template configuration files for different deployment environments. These templates provide examples of the required and optional environment variables for each environment type.

## Usage

1. **Copy the appropriate template**:
```bash
# For development
cp backend/config/templates/development.env .env

# For staging
cp backend/config/templates/staging.env .env

# For production
cp backend/config/templates/production.env .env
```

2. **Edit the configuration**:
   - Update placeholder values (account IDs, domain names, etc.)
   - Set required variables for your environment
   - Uncomment optional variables as needed

3. **Load the configuration**:
```bash
# Source the environment file
source .env

# Deploy with the configuration
./deploy-enhanced.sh --environment dev
```

## Environment Types

### Development (`development.env`)
- **Purpose**: Local development and testing
- **Domain**: Uses localhost URLs
- **Security**: Basic security settings
- **Monitoring**: Standard monitoring
- **Required Variables**: `ENVIRONMENT`, `AWS_DEFAULT_REGION`

### Staging (`staging.env`)
- **Purpose**: Pre-production testing
- **Domain**: Optional custom domain
- **Security**: Enhanced security settings
- **Monitoring**: Detailed monitoring
- **Required Variables**: `ENVIRONMENT`, `AWS_DEFAULT_REGION`

### Production (`production.env`)
- **Purpose**: Production deployment
- **Domain**: Custom domain required
- **Security**: Full security suite (WAF, Shield)
- **Monitoring**: Comprehensive monitoring and alerting
- **Required Variables**: `ENVIRONMENT`, `AWS_DEFAULT_REGION`, `DOMAIN_NAME`, `CERTIFICATE_ARN`

## Configuration Variables

### Required for All Environments

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `dev`, `staging`, `prod` |
| `AWS_DEFAULT_REGION` | AWS region for deployment | `us-east-1` |

### Required for Production Only

| Variable | Description | Example |
|----------|-------------|---------|
| `DOMAIN_NAME` | Custom domain name | `stickers.example.com` |
| `CERTIFICATE_ARN` | SSL certificate ARN | `arn:aws:acm:us-east-1:123456789012:certificate/...` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `RESOURCE_PREFIX` | Prefix for resource names | `StickerStudio` | `MyCompanyStickers` |
| `COGNITO_DOMAIN_PREFIX` | Cognito domain prefix | `sticker-studio-{env}` | `my-app-dev` |
| `CDK_DEFAULT_ACCOUNT` | AWS account ID | Auto-detected | `123456789012` |
| `LOG_RETENTION_DAYS` | CloudWatch log retention | `30` (dev), `365` (prod) | `90` |
| `ENABLE_DETAILED_MONITORING` | Detailed CloudWatch metrics | `false` | `true` |
| `ENABLE_XRAY` | X-Ray tracing | `true` | `false` |
| `SKIP_FRONTEND_BUILD` | Skip frontend build step | `false` | `true` |
| `CDK_DEBUG` | Enable CDK debug logging | `false` | `true` |

## Multi-Region Configuration

To deploy to different AWS regions, update the `AWS_DEFAULT_REGION` variable:

```bash
# US East (N. Virginia)
AWS_DEFAULT_REGION=us-east-1

# US West (Oregon)
AWS_DEFAULT_REGION=us-west-2

# Europe (Ireland)
AWS_DEFAULT_REGION=eu-west-1

# Asia Pacific (Singapore)
AWS_DEFAULT_REGION=ap-southeast-1
```

**Note**: Ensure your chosen region supports all required AWS services:
- AWS Bedrock with Stability AI Ultra model
- ECS Fargate
- Application Load Balancer
- CloudFront (global service)

## Security Considerations

### Development Environment
- Uses localhost URLs for testing
- CORS allows localhost origins
- Basic IAM policies
- Standard encryption

### Staging Environment
- Can use custom domains
- Enhanced monitoring
- Production-like security settings
- Extended log retention

### Production Environment
- **Custom domain required**
- **SSL certificate required**
- WAF protection enabled
- Shield protection enabled
- Strict CORS policies
- Comprehensive monitoring
- Extended log retention (1 year)

## Validation

The configuration system includes automatic validation:

- **Environment values**: Must be `dev`, `staging`, or `prod`
- **Region validation**: Must be a supported AWS region
- **Production requirements**: Domain and certificate must be provided
- **Resource naming**: Validates naming conventions
- **Dependencies**: Checks for required AWS services in the region

## Troubleshooting

### Common Configuration Issues

1. **Missing required variables**:
   ```
   Error: Domain name is required for production environment
   Solution: Set DOMAIN_NAME and CERTIFICATE_ARN for production
   ```

2. **Invalid environment value**:
   ```
   Error: Invalid environment 'development'. Must be one of: ['dev', 'staging', 'prod']
   Solution: Use 'dev' instead of 'development'
   ```

3. **Region not supported**:
   ```
   Error: Region 'us-gov-east-1' is not supported
   Solution: Use a commercial AWS region like 'us-east-1'
   ```

4. **Certificate ARN format**:
   ```
   Error: Invalid certificate ARN format
   Solution: Use full ARN: arn:aws:acm:region:account:certificate/id
   ```

### Validation Commands

```bash
# Test configuration loading
cd backend
python -c "
from config.environment import EnvironmentConfig
from aws_cdk import App
app = App()
config = EnvironmentConfig.from_context(app)
print('Configuration loaded successfully!')
print(f'Environment: {config.environment.value}')
print(f'Region: {config.region}')
"

# Validate region support
python -c "
from config.region_utils import RegionAdapter
region = 'us-east-1'
if RegionAdapter.validate_region(region):
    print(f'Region {region} is supported')
else:
    print(f'Region {region} is not supported')
"
```

## Best Practices

1. **Never commit sensitive values**: Use environment variables or AWS Secrets Manager
2. **Use different prefixes**: Avoid resource naming conflicts between environments
3. **Test configurations**: Validate configuration before deployment
4. **Document custom values**: Add comments for organization-specific settings
5. **Regular updates**: Keep certificate ARNs and domain configurations current
6. **Backup configurations**: Store production configurations securely
7. **Access control**: Limit access to production configuration files

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Configure Environment
  run: |
    echo "ENVIRONMENT=${{ matrix.environment }}" >> $GITHUB_ENV
    echo "AWS_DEFAULT_REGION=${{ matrix.region }}" >> $GITHUB_ENV
    if [ "${{ matrix.environment }}" = "prod" ]; then
      echo "DOMAIN_NAME=${{ secrets.PROD_DOMAIN }}" >> $GITHUB_ENV
      echo "CERTIFICATE_ARN=${{ secrets.PROD_CERT_ARN }}" >> $GITHUB_ENV
    fi

- name: Deploy
  run: ./deploy-enhanced.sh --environment ${{ matrix.environment }}
```

### AWS CodeBuild Example
```yaml
phases:
  pre_build:
    commands:
      - export ENVIRONMENT=${ENVIRONMENT:-dev}
      - export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
      - if [ "$ENVIRONMENT" = "prod" ]; then
          export DOMAIN_NAME=$PROD_DOMAIN_NAME;
          export CERTIFICATE_ARN=$PROD_CERTIFICATE_ARN;
        fi
  build:
    commands:
      - ./deploy-enhanced.sh --environment $ENVIRONMENT
```