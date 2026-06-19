#!/usr/bin/env python3
"""Update Cognito User Pool Client callback URLs with deployed domain URLs."""

import json
import os
import sys

import boto3


def build_callback_urls(outputs: dict) -> list[str]:
    urls = []

    if os.environ.get("ENVIRONMENT", "dev") == "dev":
        urls += [
            "http://localhost:3000",
            "http://localhost:3000/auth/callback",
            "https://localhost:3000",
            "https://localhost:3000/auth/callback",
        ]

    cf_domain = outputs.get("StickerStudioCloudFrontStack", {}).get("DistributionDomainName")
    if cf_domain:
        urls += [f"https://{cf_domain}", f"https://{cf_domain}/auth/callback"]

    custom_domain = os.environ.get("DOMAIN_NAME")
    if custom_domain:
        urls += [f"https://{custom_domain}", f"https://{custom_domain}/auth/callback"]

    return urls


def main():
    outputs_file = sys.argv[1] if len(sys.argv) > 1 else "frontend/outputs.json"

    with open(outputs_file, "r", encoding="utf-8") as f:
        outputs = json.load(f)

    cognito = outputs.get("StickerStudioCognitoStack", {})
    user_pool_id = cognito.get("UserPoolId")
    client_id = cognito.get("UserPoolClientId")

    if not user_pool_id or not client_id:
        print(f"Missing Cognito outputs (UserPoolId/UserPoolClientId) in {outputs_file}", file=sys.stderr)
        sys.exit(1)

    callback_urls = build_callback_urls(outputs)
    if not callback_urls:
        print("No callback URLs generated", file=sys.stderr)
        sys.exit(1)

    region = user_pool_id.split("_")[0]
    client = boto3.client("cognito-idp", region_name=region)

    resp = client.describe_user_pool_client(UserPoolId=user_pool_id, ClientId=client_id)
    config = resp["UserPoolClient"]

    client.update_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        CallbackURLs=callback_urls,
        LogoutURLs=callback_urls,
        AllowedOAuthFlows=config.get("AllowedOAuthFlows", ["code"]),
        AllowedOAuthScopes=config.get("AllowedOAuthScopes", ["openid", "email", "profile"]),
        AllowedOAuthFlowsUserPoolClient=config.get("AllowedOAuthFlowsUserPoolClient", True),
        SupportedIdentityProviders=config.get("SupportedIdentityProviders", ["COGNITO"]),
    )

    print(f"Updated Cognito client {client_id} with {len(callback_urls)} callback URLs")


if __name__ == "__main__":
    main()
