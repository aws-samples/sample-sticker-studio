from aws_cdk import (
    aws_cognito as cognito,
    CfnOutput,
    Duration,
    Stack,
)
from constructs import Construct
from config.environment import EnvironmentConfig


class CognitoStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: EnvironmentConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.config = config

        # Create User Pool
        self.user_pool = cognito.UserPool(
            self,
            "StickerBarUserPool",
            user_pool_name=config.get_resource_name("users"),
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            self_sign_up_enabled=False,
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_lowercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=Duration.days(7)
            ),
        )

        # Add domain for hosted UI
        self.user_pool_domain = cognito.UserPoolDomain(
            self,
            "StickerBarUserPoolDomain",
            user_pool=self.user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=config.cognito_domain_prefix
            ),
        )

        # Generate dynamic callback URLs based on environment
        callback_urls = config.get_cognito_callback_urls()
        logout_urls = callback_urls  # Use same URLs for logout

        # Create App Client
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "StickerBarAppClient",
            user_pool=self.user_pool,
            auth_flows=cognito.AuthFlow(
                user_srp=True,
            ),
            access_token_validity=Duration.minutes(10),
            id_token_validity=Duration.minutes(60),
            refresh_token_validity=Duration.minutes(600),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cognito.OAuthScope.OPENID, 
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PHONE,
                    cognito.OAuthScope.PROFILE
                ],
                callback_urls=callback_urls,
                logout_urls=logout_urls,
            ),
        )

        # Outputs with proper export names for cross-stack references
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name=f"{self.stack_name}-UserPoolId"
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name=f"{self.stack_name}-UserPoolClientId"
        )

        CfnOutput(
            self,
            "UserPoolDomain",
            value=self.user_pool_domain.domain_name,
            description="Cognito User Pool Domain",
            export_name=f"{self.stack_name}-UserPoolDomain"
        )

        CfnOutput(
            self,
            "CognitoCallbackUrls",
            value=",".join(callback_urls),
            description="Cognito Callback URLs",
            export_name=f"{self.stack_name}-CallbackUrls"
        )
