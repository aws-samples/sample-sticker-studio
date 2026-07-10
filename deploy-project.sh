#!/bin/bash

# Enhanced Deployment Script for AWS Sticker Studio
# This script provides comprehensive validation, error handling, and deployment orchestration

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/backend"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
OUTPUTS_FILE="${FRONTEND_DIR}/outputs.json"

# Default values
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
DRY_RUN="${DRY_RUN:-false}"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${GREEN}==== $1 ====${NC}"
}

# Error handling
cleanup() {
    local exit_code=$?
    if [ "$exit_code" -ne 0 ]; then
        log_error "Deployment failed with exit code $exit_code"
        log_info "Check the logs above for details"
        log_info "For rollback instructions, see: https://docs.aws.amazon.com/cdk/latest/guide/cli.html#cli-deploy"
    fi
    exit "$exit_code"
}

trap cleanup EXIT

# Validation functions
check_command() {
    local cmd=$1
    local install_hint=$2
    
    if ! command -v "$cmd" &> /dev/null; then
        log_error "$cmd is not installed or not in PATH"
        log_info "Install hint: $install_hint"
        return 1
    fi
    log_info "✓ $cmd is available"
    return 0
}

validate_prerequisites() {
    log_step "Validating Prerequisites"
    
    local errors=0
    
    # Check required commands
    check_command "aws" "Install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html" || ((errors++))
    check_command "cdk" "Install CDK: npm install -g aws-cdk@2.233.0" || ((errors++))
    check_command "node" "Install Node.js: https://nodejs.org/" || ((errors++))
    check_command "npm" "Install npm (comes with Node.js)" || ((errors++))
    check_command "uv" "Install uv: https://docs.astral.sh/uv/getting-started/installation/" || ((errors++))
    
    # Check Docker (or CDK_DOCKER alternative like finch)
    local docker_cmd="${CDK_DOCKER:-docker}"
    if ! command -v "$docker_cmd" &> /dev/null; then
        log_error "$docker_cmd is not installed or not in PATH"
        log_info "Install Docker: https://docs.docker.com/get-docker/"
        log_info "Or set CDK_DOCKER to an alternative (e.g. export CDK_DOCKER=finch)"
        ((errors++))
    elif ! "$docker_cmd" info &> /dev/null; then
        log_error "$docker_cmd is installed but the daemon is not running"
        log_info "Start the $docker_cmd daemon and try again"
        ((errors++))
    else
        log_info "✓ $docker_cmd is available and running"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        log_info "Configure credentials: aws configure"
        ((errors++))
    else
        local account_id
        account_id=$(aws sts get-caller-identity --query Account --output text)
        local user_arn
        user_arn=$(aws sts get-caller-identity --query Arn --output text)
        log_info "✓ AWS credentials valid - Account: $account_id"
        log_info "✓ User/Role: $user_arn"
    fi
    
    # Check CDK bootstrap
    if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region "$AWS_REGION" &> /dev/null; then
        log_warning "CDK not bootstrapped in region $AWS_REGION"
        log_info "Bootstrap CDK: cdk bootstrap aws://${AWS_ACCOUNT_ID-"account-id"}/$AWS_REGION"
        log_info "Attempting to bootstrap automatically..."
        
        if [ "$DRY_RUN" = "false" ]; then
            cdk bootstrap "aws://$(aws sts get-caller-identity --query Account --output text)/$AWS_REGION"
            log_success "CDK bootstrap completed"
        else
            log_info "[DRY RUN] Would bootstrap CDK"
        fi
    else
        log_info "✓ CDK is bootstrapped in $AWS_REGION"
    fi
    
    # Check directories
    if [ ! -d "$BACKEND_DIR" ]; then
        log_error "Backend directory not found: $BACKEND_DIR"
        ((errors++))
    else
        log_info "✓ Backend directory exists"
    fi
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        log_error "Frontend directory not found: $FRONTEND_DIR"
        ((errors++))
    else
        log_info "✓ Frontend directory exists"
    fi
    
    # Sync Python dependencies with uv
    log_info "Syncing Python dependencies with uv..."
    (cd "$BACKEND_DIR" && uv sync --all-groups)
    log_info "✓ Python dependencies synced"
    
    if [ "$errors" -gt 0 ]; then
        log_error "Prerequisites validation failed with $errors errors"
        exit 1
    fi
    
    log_success "All prerequisites validated successfully"
}

validate_environment_config() {
    log_step "Validating Environment Configuration"

    local errors=0

    # --- Core configuration ---
    log_info "ENVIRONMENT          = ${ENVIRONMENT}"
    case "$ENVIRONMENT" in
        dev|staging|prod)
            log_info "✓ Valid environment"
            ;;
        *)
            log_error "Invalid ENVIRONMENT '${ENVIRONMENT}' (must be dev, staging, or prod)"
            ((errors++))
            ;;
    esac

    log_info "AWS_REGION           = ${AWS_REGION}"
    if [ -z "$AWS_REGION" ]; then
        log_error "AWS_REGION is required"
        ((errors++))
    fi

    # --- Domain & SSL (required for prod, optional otherwise) ---
    if [ "$ENVIRONMENT" = "prod" ]; then
        log_info "DOMAIN_NAME          = ${DOMAIN_NAME:-<not set>}"
        log_info "CERTIFICATE_ARN      = ${CERTIFICATE_ARN:-<not set>}"

        if [ -z "${DOMAIN_NAME:-}" ]; then
            log_error "DOMAIN_NAME is required for production environment"
            ((errors++))
        fi
        if [ -z "${CERTIFICATE_ARN:-}" ]; then
            log_error "CERTIFICATE_ARN is required for production environment"
            ((errors++))
        fi
        if [ -n "${CERTIFICATE_ARN:-}" ] && [[ ! "$CERTIFICATE_ARN" =~ ^arn:aws:acm: ]]; then
            log_error "CERTIFICATE_ARN does not look like a valid ACM ARN"
            ((errors++))
        fi
    fi

    # --- Resource configuration ---
    log_info "RESOURCE_PREFIX      = ${RESOURCE_PREFIX:-StickerStudio} (default: StickerStudio)"
    log_info "COGNITO_DOMAIN_PREFIX= ${COGNITO_DOMAIN_PREFIX:-sticker-studio-${ENVIRONMENT}} (default: sticker-studio-${ENVIRONMENT})"

    # --- AWS account ---
    log_info "CDK_DEFAULT_ACCOUNT  = ${CDK_DEFAULT_ACCOUNT:-<auto-detect>}"
    log_info "CDK_DEFAULT_REGION   = ${CDK_DEFAULT_REGION:-<not set>}"

    # --- Deployment control ---
    log_info "DRY_RUN              = ${DRY_RUN}"

    # --- Monitoring (informational) ---
    log_info "LOG_RETENTION_DAYS   = ${LOG_RETENTION_DAYS:-<default per environment>}"
    log_info "ENABLE_DETAILED_MONITORING = ${ENABLE_DETAILED_MONITORING:-<default per environment>}"
    log_info "ENABLE_XRAY          = ${ENABLE_XRAY:-<default per environment>}"

    # --- Container runtime ---
    log_info "CDK_DOCKER           = ${CDK_DOCKER:-docker} (default: docker, set to 'finch' for Finch)"

    # --- Debug ---
    log_info "CDK_DEBUG            = ${CDK_DEBUG:-false}"
    log_info "DEBUG                = ${DEBUG:-false}"

    # --- Result ---
    if [ "$errors" -gt 0 ]; then
        log_error "Environment configuration validation failed with $errors error(s)"
        log_info "See ENVIRONMENT_VARIABLES.md for full reference"
        exit 1
    fi

    log_success "Environment configuration validated"

    # Ask user to confirm before proceeding
    if [ "$DRY_RUN" = "false" ]; then
        echo ""
        read -rp "$(echo -e "${YELLOW}Proceed with deployment? [y/N]:${NC} ")" confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled by user"
            exit 0
        fi
    fi
}

deploy_infrastructure() {
    log_step "Deploying Infrastructure"
    
    cd "$BACKEND_DIR"
    
    # Set CDK context
    local cdk_context=(
        --context "environment=$ENVIRONMENT"
        --context "region=$AWS_REGION"
    )
    
    if [ -n "${DOMAIN_NAME:-}" ]; then
        cdk_context+=(--context "domain_name=$DOMAIN_NAME")
    fi
    
    if [ -n "${CERTIFICATE_ARN:-}" ]; then
        cdk_context+=(--context "certificate_arn=$CERTIFICATE_ARN")
    fi
    
    if [ -n "${COGNITO_DOMAIN_PREFIX:-}" ]; then
        cdk_context+=(--context "cognito_domain_prefix=$COGNITO_DOMAIN_PREFIX")
    fi
    
    # Synthesize templates (dry run only)
    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY RUN] Synthesizing CDK templates..."
        cdk synth "${cdk_context[@]}" --all
        return 0
    fi
    
    # Deploy all stacks (CDK handles dependency ordering)
    log_info "Deploying all stacks..."
    cdk deploy "${cdk_context[@]}" \
        --all \
        --require-approval never \
        --outputs-file "$OUTPUTS_FILE"
    
    cd "$SCRIPT_DIR"
    log_success "Infrastructure deployment completed"
    
    # Update Cognito callback URLs after successful CloudFront deployment
    update_cognito_callbacks

    # Redeploy CORS-dependent stacks with the now-known CloudFront domain
    redeploy_cors_stacks
}

update_cognito_callbacks() {
    log_step "Updating Cognito Callback URLs"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY RUN] Would update Cognito callback URLs"
        return 0
    fi
    
    # Check if the update script exists
    if [ ! -f "update-cognito-callbacks.py" ]; then
        log_warning "Cognito callback update script not found, skipping callback URL update"
        return 0
    fi
    
    # Check if outputs file exists
    if [ ! -f "$OUTPUTS_FILE" ]; then
        log_warning "Outputs file not found, skipping callback URL update"
        return 0
    fi
    
    log_info "Executing Cognito callback URL update..."
    
    # Run the callback URL update script with error handling
    if uv run --project "$BACKEND_DIR" python update-cognito-callbacks.py "$OUTPUTS_FILE"; then
        log_success "Cognito callback URLs updated successfully"
        return 0
    else
        local exit_code=$?
        log_warning "Cognito callback URL update failed with exit code $exit_code"
        log_warning "This is not a critical error - deployment can continue"
        log_info "You can manually update callback URLs later by running:"
        log_info "  uv run --project backend python update-cognito-callbacks.py frontend/outputs.json"
        return 0  # Don't fail the entire deployment
    fi
}

redeploy_cors_stacks() {
    # Skip if using a custom domain (CORS already correct)
    if [ -n "${DOMAIN_NAME:-}" ]; then
        return 0
    fi

    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY RUN] Would redeploy CORS stacks with CloudFront domain"
        return 0
    fi

    if [ ! -f "$OUTPUTS_FILE" ]; then
        return 0
    fi

    local cf_domain
    cf_domain=$(jq -r '.StickerStudioCloudFrontStack.DistributionDomainName // ""' "$OUTPUTS_FILE")

    if [ -z "$cf_domain" ]; then
        log_warning "CloudFront domain not found, skipping CORS redeploy"
        return 0
    fi

    log_step "Locking down CORS with CloudFront domain: $cf_domain"

    cd "$BACKEND_DIR"

    local cdk_context=(
        --context "environment=$ENVIRONMENT"
        --context "region=$AWS_REGION"
        --context "cloudfront_domain=$cf_domain"
    )

    if [ -n "${COGNITO_DOMAIN_PREFIX:-}" ]; then
        cdk_context+=(--context "cognito_domain_prefix=$COGNITO_DOMAIN_PREFIX")
    fi

    # Redeploy stacks that depend on CloudFront domain (CORS origins + Cognito callbacks)
    cdk deploy "${cdk_context[@]}" \
        StickerStudioCognitoStack \
        StickerStudioBucketStack \
        StickerStudioApiStack \
        StickerStudioCloudFrontStack \
        --require-approval never \
        --outputs-file "$OUTPUTS_FILE"

    cd "$SCRIPT_DIR"
    log_success "CORS stacks updated with CloudFront domain"
}

validate_deployment_outputs() {
    log_step "Validating Deployment Outputs"
    
    if [ ! -f "$OUTPUTS_FILE" ]; then
        log_error "Outputs file not found: $OUTPUTS_FILE"
        return 1
    fi
    
    # Check for required outputs
    local required_outputs=(
        "StickerStudioBucketStack.ImageStorageBucketName"
        "StickerStudioCognitoStack.UserPoolId"
        "StickerStudioCognitoStack.UserPoolClientId"
        "StickerStudioApiStack.ApiGatewayUrl"
        "StickerStudioFargateStack.LoadBalancerUrl"
        "StickerStudioCloudFrontStack.DistributionDomainName"
    )
    
    local missing_outputs=()
    for output in "${required_outputs[@]}"; do
        local stack="${output%%.*}"
        local key="${output#*.}"
        if ! jq -e --arg s "$stack" --arg k "$key" '.[$s][$k]' "$OUTPUTS_FILE" &> /dev/null; then
            missing_outputs+=("$output")
        fi
    done
    
    if [ ${#missing_outputs[@]} -gt 0 ]; then
        log_error "Missing required outputs:"
        for output in "${missing_outputs[@]}"; do
            log_error "  - $output"
        done
        return 1
    fi
    
    log_success "All required outputs are present"
    return 0
}

print_deployment_summary() {
    log_step "Deployment Summary"
    
    local account_id
    account_id=$(aws sts get-caller-identity --query Account --output text)
    
    echo "Deployment completed successfully!"
    echo ""
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo "Account: $account_id"
    echo ""
    
    if [ -f "$OUTPUTS_FILE" ]; then
        echo "Key URLs:"
        
        # Extract URLs from outputs
        local api_url
        api_url=$(jq -r '.StickerStudioApiStack.ApiGatewayUrl // "N/A"' "$OUTPUTS_FILE")
        local lb_url
        lb_url=$(jq -r '.StickerStudioFargateStack.LoadBalancerUrl // "N/A"' "$OUTPUTS_FILE")
        local cf_domain
        cf_domain=$(jq -r '.StickerStudioCloudFrontStack.DistributionDomainName // "N/A"' "$OUTPUTS_FILE")
        
        echo "  API Gateway: $api_url"
        echo "  Load Balancer: http://$lb_url (internal only — configure HTTPS for production)"
        echo "  CloudFront: https://$cf_domain"
        
        if [ -n "${DOMAIN_NAME:-}" ]; then
            echo "  Custom Domain: https://$DOMAIN_NAME"
        fi
        
        echo ""
        echo "Configuration files:"
        echo "  CDK Outputs: $OUTPUTS_FILE"
    fi
    
    echo ""
    echo "Next steps:"
    echo "  1. Test the application endpoints above"
    echo "  2. Verify Cognito authentication works with deployed domains"
    echo "  3. Configure DNS (if using custom domain)"
    echo "  4. Set up monitoring and alerts"
    echo ""
    echo "Note: Cognito callback URLs have been automatically updated to include deployed domains."
}

show_usage() {
    cat << EOF
Enhanced Deployment Script for AWS Sticker Studio

Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV    Deployment environment (dev|staging|prod) [default: dev]
    -r, --region REGION      AWS region [default: us-east-1]
    -d, --domain DOMAIN      Custom domain name (required for prod)
    -c, --certificate ARN    Certificate ARN (required for prod)
    --dry-run               Show what would be deployed without making changes
    -h, --help              Show this help message

Environment Variables:
    ENVIRONMENT             Same as --environment
    AWS_REGION              Same as --region
    DOMAIN_NAME             Same as --domain
    CERTIFICATE_ARN         Same as --certificate
    COGNITO_DOMAIN_PREFIX   Cognito domain prefix
    DRY_RUN                 Same as --dry-run

Examples:
    # Deploy to development
    $0 --environment dev

    # Deploy to production with custom domain
    $0 --environment prod --domain example.com --certificate arn:aws:acm:...

    # Dry run to see what would be deployed
    $0 --environment staging --dry-run

Features:
    - Automatic CDK stack deployment with proper dependency ordering
    - Comprehensive validation and error handling
    - Automatic Cognito callback URL updates after CloudFront deployment
    - Multi-environment support with configuration validation

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN_NAME="$2"
            shift 2
            ;;
        -c|--certificate)
            CERTIFICATE_ARN="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "Starting enhanced deployment for AWS Sticker Studio"
    log_info "Script directory: $SCRIPT_DIR"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_warning "DRY RUN MODE - No actual changes will be made"
    fi
    
    validate_prerequisites
    validate_environment_config
    deploy_infrastructure
    
    if [ "$DRY_RUN" = "false" ]; then
        validate_deployment_outputs
        print_deployment_summary
    else
        log_info "[DRY RUN] Deployment validation completed successfully"
    fi
    
    log_success "Deployment process completed successfully!"
}

# Run main function
main "$@"