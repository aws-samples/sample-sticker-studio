from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    aws_iam,
    aws_lambda,
    aws_apigateway,
    Duration,
    Stack,
    aws_dynamodb as dynamodb,
)
from constructs import Construct
from config.environment import EnvironmentConfig, get_region_specific_layer_arn
from stacks.bucketStack import BucketStack
from stacks.cognitoStack import CognitoStack


class ApiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        bucket_stack: BucketStack,
        cognito_stack: CognitoStack,
        config: EnvironmentConfig,
        **kwargs,
    ) -> None:

        super().__init__(scope, id, **kwargs)
        self.config = config
        self.bucket_stack = bucket_stack
        self.nag_suppressed_resources = []

        # Create DynamoDB logging table
        logging_table = dynamodb.Table(
            self,
            "LoggingTable",
            partition_key=dynamodb.Attribute(
                name="request_id", type=dynamodb.AttributeType.STRING
            ),
            table_name=config.get_resource_name("logging-table"),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy = RemovalPolicy.DESTROY if config.environment.value == 'dev' else RemovalPolicy.RETAIN,
        )
        # Note: Lambda must include 'ttl' attribute (epoch seconds) when writing items

        # Create Lambda role with least privilege
        self.lambda_role = aws_iam.Role(
            self,
            "StickerBarGenerateImageLambdaRole",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=config.get_resource_name("lambda-role")
        )

        # Create granular IAM policies for Lambda with specific resource ARNs
        lambda_policy_document = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    sid="BedrockAccess",
                    actions=["bedrock:InvokeModel"],
                    resources=[
                        f"arn:aws:bedrock:{config.bedrock_region}::foundation-model/stability.stable-image-ultra-v1:1",
                        f"arn:aws:bedrock:{config.bedrock_region}:{self.account}:inference-profile/*",
                    ],
                ),
                aws_iam.PolicyStatement(
                    sid="CloudWatchLogs",
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream", 
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/{config.get_resource_name('generate-image')}*"
                    ],
                ),
                aws_iam.PolicyStatement(
                    sid="S3BucketAccess",
                    actions=["s3:GetObject", "s3:PutObject"],
                    resources=[f"{bucket_stack.storage_bucket_arn}/*"],
                ),
                aws_iam.PolicyStatement(
                    sid="S3BucketList",
                    actions=["s3:ListBucket"],
                    resources=[bucket_stack.storage_bucket_arn],
                ),
                aws_iam.PolicyStatement(
                    sid="DynamoDBAccess",
                    actions=[
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem"
                    ],
                    resources=[logging_table.table_arn],
                ),
                aws_iam.PolicyStatement(
                    sid="KMSAccess",
                    actions=[
                        "kms:Decrypt",
                        "kms:GenerateDataKey",
                    ],
                    resources=[bucket_stack.bucket_key_arn],
                ),
            ]
        )

        policy_lambda = aws_iam.Policy(
            self, f"{self.stack_name}-policy", document=lambda_policy_document
        )

        self.lambda_role.attach_inline_policy(policy_lambda)
        self.nag_suppressed_resources.extend([policy_lambda, self.lambda_role])

        # Get region-appropriate Lambda layers
        pillow_layer_arn = get_region_specific_layer_arn(config.region, "pillow")
        
        # Build layers list with available layers only
        layers = []
        if pillow_layer_arn:
            layers.append(aws_lambda.LayerVersion.from_layer_version_arn(
                self, "PillowLayer", pillow_layer_arn
            ))

        # Create Lambda function
        self.lambda_function = aws_lambda.Function(
            self,
            "StickerBarGenerateImageLambda",
            function_name=config.get_resource_name("generate-image"),
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(90),
            memory_size=1024,
            role=self.lambda_role,
            code=aws_lambda.Code.from_asset("src/lambda/generateImage"),
            handler="main.lambda_handler",
            environment={
                "STORAGE_BUCKET": bucket_stack.storage_bucket_name,
                "LOG_TABLE_NAME": logging_table.table_name,
                "ALLOWED_ORIGIN": config.security.cors_allowed_origins[0] if config.security.cors_allowed_origins else '*',
                "BEDROCK_REGION": config.bedrock_region,
            },
            layers=layers if layers else None,
        )

        # Create API Gateway with environment-specific CORS
        api = aws_apigateway.RestApi(
            self,
            "GenerateImageAPI",
            rest_api_name=config.get_resource_name("api"),
            endpoint_configuration=aws_apigateway.EndpointConfiguration(
                types=[aws_apigateway.EndpointType.REGIONAL]
            ),
            default_cors_preflight_options=aws_apigateway.CorsOptions(
                allow_origins=config.security.cors_allowed_origins,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                ],
            ),
            deploy=True,
            deploy_options=aws_apigateway.StageOptions(
                stage_name=config.environment.value,
            ),
        )

        # Create API Gateway integration with Lambda
        integration = aws_apigateway.LambdaIntegration(
            self.lambda_function, proxy=True, timeout=Duration.seconds(29)
        )

        # Create Cognito authorizer
        authorizer = aws_apigateway.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[cognito_stack.user_pool]
        )

        # Add a specific resource for handling payloads
        generate_image_resource = api.root.add_resource("generateImages")

        # Add POST method with request validator
        # Define the request model
        request_model = api.add_model(
            "generateimagesmodel",
            content_type="application/json",
            model_name="generateimages",
            schema=aws_apigateway.JsonSchema(
                type=aws_apigateway.JsonSchemaType.OBJECT,
                required=["character", "activity", "location"],
                properties={
                    "character": aws_apigateway.JsonSchema(
                        type=aws_apigateway.JsonSchemaType.STRING
                    ),
                    "activity": aws_apigateway.JsonSchema(
                        type=aws_apigateway.JsonSchemaType.STRING
                    ),
                    "location": aws_apigateway.JsonSchema(
                        type=aws_apigateway.JsonSchemaType.STRING
                    ),
                },
            ),
        )

        # Add POST method with request validation
        generate_image_resource.add_method(
            "POST",
            integration,
            request_models={"application/json": request_model},
            request_validator_options=aws_apigateway.RequestValidatorOptions(
                validate_request_body=True
            ),
            authorization_type=aws_apigateway.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        # Output the API Gateway URL with proper export name
        CfnOutput(
            self, 
            "ApiGatewayUrl", 
            description="API Gateway endpoint URL", 
            value=api.url,
            export_name=f"{self.stack_name}-ApiUrl"
        )

        # Store API reference for cross-stack usage
        self.api_gateway = api
