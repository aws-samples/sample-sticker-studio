"""
Region Adaptation Utilities for AWS Sticker Studio

Provides region validation, Lambda layer ARN generation, and resource adaptation.
"""

import json
from typing import Dict, List, Optional

import requests

SUPPORTED_REGIONS = {
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-central-1",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
}

_KLAYERS_API = "https://api.klayers.cloud/api/v2/p3.12/layers/latest/{region}/"
_REQUIRED_LAYERS = {"pillow": "Pillow"}

# Cache to avoid repeated API calls during a single synth
_region_layers_cache: Dict[str, Dict[str, str]] = {}


def _fetch_region_layers(region: str) -> Dict[str, str]:
    """Fetch all latest layer ARNs for a region from Klayers API. Returns {package: arn}."""
    if region in _region_layers_cache:
        return _region_layers_cache[region]

    url = _KLAYERS_API.format(region=region)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        layers = {item["package"]: item["arn"] for item in data if "arn" in item}
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        layers = {}

    _region_layers_cache[region] = layers
    return layers


class RegionAdapter:
    """Utility class for adapting resources to different AWS regions."""

    @classmethod
    def validate_region(cls, region: str) -> bool:
        return region in SUPPORTED_REGIONS

    @classmethod
    def get_supported_regions(cls) -> List[str]:
        return sorted(SUPPORTED_REGIONS)

    @classmethod
    def validate_region_constraints(cls, region: str, requirements: Dict[str, any]) -> List[str]:
        errors = []
        if region not in SUPPORTED_REGIONS:
            errors.append(f"Region {region} is not supported")
        return errors

    @classmethod
    def get_lambda_layer_arn(cls, region: str, layer_name: str) -> Optional[str]:
        if region not in SUPPORTED_REGIONS or layer_name not in _REQUIRED_LAYERS:
            return None
        layers = _fetch_region_layers(region)
        return layers.get(_REQUIRED_LAYERS[layer_name])


def adapt_resources_for_region(region: str) -> Dict[str, any]:
    """Return region-adapted configuration dict."""
    if not RegionAdapter.validate_region(region):
        raise ValueError(f"Region {region} is not supported")

    return {
        "region": region,
        "lambda_layers": {
            name: RegionAdapter.get_lambda_layer_arn(region, name)
            for name in _REQUIRED_LAYERS
        },
        "bedrock_model": "stability.stable-image-ultra-v1:1",
        "supports_bedrock": True,
        "supports_fargate": True,
    }
