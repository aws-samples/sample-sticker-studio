from aws_cdk import (
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    CfnOutput,
    Stack,
    Duration,
)
from constructs import Construct
from config.environment import EnvironmentConfig
from stacks.fargateStack import FargateStack


class CloudFrontStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        fargate_stack: FargateStack,
        config: EnvironmentConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = config
        self.fargate_stack = fargate_stack

        # Secret header value for origin verification
        origin_verify_header = {
            "X-Origin-Verify": fargate_stack.origin_verify_secret.secret_value.unsafe_unwrap()
        }

        # Create response headers policy with basic security headers (CSP removed temporarily)
        self.security_headers_policy = cloudfront.ResponseHeadersPolicy(
            self,
            "SecurityHeadersPolicy",
            response_headers_policy_name=config.get_resource_name("security-headers"),
            cors_behavior=cloudfront.ResponseHeadersCorsBehavior(
                access_control_allow_credentials=False,
                access_control_allow_headers=["*"],
                access_control_allow_methods=[
                    "GET",
                    "HEAD",
                    "POST",
                    "PUT",
                    "PATCH",
                    "DELETE",
                    "OPTIONS",
                ],
                access_control_allow_origins=config.security.cors_allowed_origins,
                access_control_max_age=Duration.seconds(600),
                origin_override=True,
            ),
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                # CSP temporarily removed due to compatibility issues with Next.js
                # TODO: Re-implement CSP with proper Next.js nonce support
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.seconds(31536000),  # 1 year
                    include_subdomains=True,
                    preload=True,
                    override=True,
                ),
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(
                    override=True,
                ),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY,
                    override=True,
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
                    override=True,
                ),
            ),
        )

        # Cache policy for Next.js image optimization (forwards all query strings)
        self.nextjs_image_cache_policy = cloudfront.CachePolicy(
            self,
            "NextjsImageCachePolicy",
            cache_policy_name=config.get_resource_name("nextjs-image-cache"),
            default_ttl=Duration.days(30),
            max_ttl=Duration.days(365),
            min_ttl=Duration.seconds(0),
            header_behavior=cloudfront.CacheHeaderBehavior.allow_list("Accept"),
            query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
            cookie_behavior=cloudfront.CacheCookieBehavior.none(),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
        )

        # Determine origin protocol policy based on whether TLS is configured on the ALB
        # When a certificate is available, use HTTPS_ONLY for encrypted origin connections
        # Otherwise, fall back to HTTP_ONLY (dev environments without custom domains)
        origin_protocol = (
            cloudfront.OriginProtocolPolicy.HTTPS_ONLY
            if config.domain_name and config.certificate_arn
            else cloudfront.OriginProtocolPolicy.HTTP_ONLY
        )
        origin_port = 443 if config.domain_name and config.certificate_arn else 80

        # Create CloudFront distribution with security enhancements
        distribution_config = {
            "default_behavior": cloudfront.BehaviorOptions(
                origin=origins.LoadBalancerV2Origin(
                    fargate_stack.fargate_service.load_balancer,
                    protocol_policy=origin_protocol,
                    http_port=80,
                    https_port=443,
                    connection_attempts=3,
                    connection_timeout=Duration.seconds(10),
                    read_timeout=Duration.seconds(60),
                    custom_headers=origin_verify_header,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                response_headers_policy=self.security_headers_policy,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
            ),
            "price_class": cloudfront.PriceClass.PRICE_CLASS_100,  # Cost optimization
            "enabled": True,
            "http_version": cloudfront.HttpVersion.HTTP2_AND_3,
            "additional_behaviors": {
                "/_next/static/*": cloudfront.BehaviorOptions(
                    origin=origins.LoadBalancerV2Origin(
                        fargate_stack.fargate_service.load_balancer,
                        protocol_policy=origin_protocol,
                        http_port=80,
                        https_port=443,
                        custom_headers=origin_verify_header,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    response_headers_policy=self.security_headers_policy,
                ),
                "/_next/image*": cloudfront.BehaviorOptions(
                    origin=origins.LoadBalancerV2Origin(
                        fargate_stack.fargate_service.load_balancer,
                        protocol_policy=origin_protocol,
                        http_port=80,
                        https_port=443,
                        custom_headers=origin_verify_header,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=self.nextjs_image_cache_policy,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                    response_headers_policy=self.security_headers_policy,
                    compress=True,
                ),
            },
        }

        # Add custom domain support if configured
        if config.domain_name and config.certificate_arn:
            certificate = acm.Certificate.from_certificate_arn(
                self, "Certificate", config.certificate_arn
            )
            distribution_config.update(
                {
                    "domain_names": [config.domain_name],
                    "certificate": certificate,
                    "minimum_protocol_version": cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
                    "ssl_support_method": cloudfront.SSLMethod.SNI,
                }
            )

        self.distribution = cloudfront.Distribution(
            self, "Distribution", **distribution_config
        )


        # Output the CloudFront URL with proper export name
        CfnOutput(
            self,
            "DistributionDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
            export_name=f"{self.stack_name}-DistributionDomain",
        )

        if config.domain_name:
            CfnOutput(
                self,
                "CustomDomainName",
                value=config.domain_name,
                description="Custom Domain Name",
                export_name=f"{self.stack_name}-CustomDomain",
            )
