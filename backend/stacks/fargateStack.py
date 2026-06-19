from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_certificatemanager as acm,
    CfnOutput,
    Stack,
    Duration,
    CustomResource,
    custom_resources as cr,
)
from constructs import Construct
from config.environment import EnvironmentConfig
from stacks.cognitoStack import CognitoStack
from stacks.apiStack import ApiStack
import json


class FargateStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cognito_stack: CognitoStack,
        api_stack: ApiStack,
        config: EnvironmentConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = config
        self.cognito_stack = cognito_stack
        self.api_stack = api_stack

        vpc = ec2.Vpc(
            self, "MyVpc", vpc_name=config.get_resource_name("vpc"), max_azs=2
        )

        cluster = ecs.Cluster(
            self, "MyCluster", vpc=vpc, cluster_name=config.get_resource_name("cluster")
        )

        # Create the Fargate Service with ALB listener and dynamic environment variables
        # open_listener=False prevents CDK from automatically adding a 0.0.0.0/0 ingress rule
        # to the ALB security group, so we can restrict it to CloudFront only.
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "NextJsFargateService",
            cluster=cluster,
            cpu=512,
            desired_count=2,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    "../frontend/",
                    platform=aws_ecr_assets.Platform.LINUX_ARM64,
                    cache_from=[aws_ecr_assets.DockerCacheOption(type="inline")],
                ),
                container_port=3000,
                environment={
                    "NODE_ENV": "production",
                    "NEXT_PUBLIC_COGNITO_REGION": config.region,
                    "NEXT_PUBLIC_COGNITO_USER_POOL_ID": cognito_stack.user_pool.user_pool_id,
                    "NEXT_PUBLIC_COGNITO_CLIENT_ID": cognito_stack.user_pool_client.user_pool_client_id,
                    "NEXT_PUBLIC_COGNITO_DOMAIN": cognito_stack.user_pool_domain.domain_name,
                    "NEXT_PUBLIC_API_URL": api_stack.api_gateway.url,
                    "APP_URL": "http://localhost:3000",  # Fallback only; deployed environments derive URL from request Host header
                    "ENVIRONMENT": config.environment.value,
                },
            ),
            memory_limit_mib=1024,
            public_load_balancer=True,
            open_listener=False,  # Prevents the default 0.0.0.0/0 ingress rule from being added
            assign_public_ip=True,
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64,
            ),
        )

        # Create secret for CloudFront origin verification header
        self.origin_verify_secret = secretsmanager.Secret(
            self,
            "OriginVerifySecret",
            secret_name=config.get_resource_name("origin-verify-secret"),
            description="Secret header value for CloudFront origin verification",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                password_length=64,
            ),
        )

        # Add HTTPS listener on port 443 for encrypted CloudFront-to-origin communication
        # Uses an ACM certificate for the ALB domain if configured, otherwise uses HTTP fallback
        if config.domain_name and config.certificate_arn:
            alb_certificate = acm.Certificate.from_certificate_arn(
                self, "AlbCertificate", config.certificate_arn
            )
            self.https_listener = self.fargate_service.load_balancer.add_listener(
                "HttpsListener",
                port=443,
                protocol=elbv2.ApplicationProtocol.HTTPS,
                certificates=[alb_certificate],
                default_action=elbv2.ListenerAction.fixed_response(
                    status_code=403,
                    content_type="text/plain",
                    message_body="Forbidden",
                ),
            )

            # Only forward HTTPS requests with the correct origin verify header
            self.https_listener.add_action(
                "AllowCloudFrontOriginHttps",
                action=elbv2.ListenerAction.forward(
                    [self.fargate_service.target_group]
                ),
                conditions=[
                    elbv2.ListenerCondition.http_header(
                        "X-Origin-Verify",
                        [self.origin_verify_secret.secret_value.unsafe_unwrap()],
                    )
                ],
                priority=1,
            )

        # Change ALB HTTP listener default action to 403 (deny direct access)
        cfn_listener = self.fargate_service.listener.node.default_child
        cfn_listener.default_actions = [
            {
                "type": "fixed-response",
                "fixedResponseConfig": {
                    "statusCode": "403",
                    "contentType": "text/plain",
                    "messageBody": "Forbidden",
                },
            }
        ]

        # Only forward HTTP requests that include the correct origin verify header
        self.fargate_service.listener.add_action(
            "AllowCloudFrontOrigin",
            action=elbv2.ListenerAction.forward(
                [self.fargate_service.target_group]
            ),
            conditions=[
                elbv2.ListenerCondition.http_header(
                    "X-Origin-Verify",
                    [self.origin_verify_secret.secret_value.unsafe_unwrap()],
                )
            ],
            priority=1,
        )

        # Restrict ALB security group to only accept traffic from CloudFront
        alb_security_group = (
            self.fargate_service.load_balancer.connections.security_groups[0]
        )

        # Get CloudFront managed prefix list ID dynamically
        # The prefix list ID varies by region, so we look it up by name
        # This is a global managed prefix list that contains all CloudFront IP ranges
        cloudfront_prefix_list_id = self._get_cloudfront_prefix_list_id()

        # Add ingress rule for HTTPS from CloudFront only
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.prefix_list(cloudfront_prefix_list_id),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from CloudFront only",
        )

        # Add ingress rule for HTTP from CloudFront (fallback for non-TLS environments)
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.prefix_list(cloudfront_prefix_list_id),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from CloudFront only",
        )

        # Add health check to the target group
        self.fargate_service.target_group.configure_health_check(
            path="/api/health",
            healthy_http_codes="200,301,302",
            timeout=Duration.seconds(10),
            interval=Duration.seconds(15),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        # Reduce deregistration delay from default 300s to speed up rolling updates
        self.fargate_service.target_group.set_attribute(
            "deregistration_delay.timeout_seconds", "30"
        )

        # NOTE: Deployment circuit breaker and faster rolling updates are intentionally
        # disabled for this demo application. In production, uncomment the below to enable
        # auto-rollback on deployment failures and allow 50% minimum healthy during deploys.
        # This is disabled here to simplify initial deployment and debugging.

        # # Access the L1 CfnService for property overrides
        # cfn_service = self.fargate_service.service.node.default_child

        # # Allow faster rolling updates by permitting 50% minimum healthy during deploy
        # cfn_service.add_property_override(
        #     "DeploymentConfiguration",
        #     {
        #         "MinimumHealthyPercent": 50,
        #         "MaximumPercent": 200,
        #     },
        # )

        # # Enable circuit breaker for faster failure detection and auto-rollback
        # cfn_service.add_property_override(
        #     "DeploymentConfiguration.DeploymentCircuitBreaker",
        #     {"Enable": True, "Rollback": True},
        # )

        # Add standard tags for cost tracking and management
        self._add_standard_tags()

        self.fargate_service.load_balancer.set_attribute(
            "idle_timeout.timeout_seconds", "120"
        )

        # Output the Load Balancer URL for CloudFront stack reference
        CfnOutput(
            self,
            "LoadBalancerUrl",
            value=self.fargate_service.load_balancer.load_balancer_dns_name,
            description="Application Load Balancer DNS Name",
            export_name=f"{self.stack_name}-LoadBalancerUrl",
        )

    def _add_standard_tags(self):
        """Add standard tags for cost tracking and management"""
        from aws_cdk import Tags

        Tags.of(self).add("Environment", self.config.environment.value)
        Tags.of(self).add("Project", "StickerStudio")
        Tags.of(self).add(
            "CostCenter", f"StickerStudio-{self.config.environment.value}"
        )
        Tags.of(self).add("ManagedBy", "CDK")
        Tags.of(self).add("Region", self.config.region)

    def _get_cloudfront_prefix_list_id(self) -> str:
        """
        Get the CloudFront managed prefix list ID for the current region.
        The prefix list ID varies by region, so we use a custom resource to look it up.
        """
        # Create a custom resource to look up the CloudFront prefix list ID
        get_prefix_list = cr.AwsCustomResource(
            self,
            "GetCloudFrontPrefixList",
            on_create=cr.AwsSdkCall(
                service="EC2",
                action="describeManagedPrefixLists",
                parameters={
                    "Filters": [
                        {
                            "Name": "prefix-list-name",
                            "Values": ["com.amazonaws.global.cloudfront.origin-facing"],
                        }
                    ]
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "CloudFrontPrefixListLookup"
                ),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                statements=[
                    iam.PolicyStatement(
                        actions=["ec2:DescribeManagedPrefixLists"],
                        resources=["*"],  # Required: DescribeManagedPrefixLists does not support resource-level permissions
                    )
                ]
            ),
        )

        # Extract the prefix list ID from the response
        return get_prefix_list.get_response_field("PrefixLists.0.PrefixListId")
