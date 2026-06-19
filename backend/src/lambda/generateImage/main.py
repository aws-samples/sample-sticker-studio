import json
import boto3
import base64
import logging
from botocore.config import Config
from botocore.exceptions import ClientError
import os
import io
import tempfile
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import math
import secrets
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

MODEL_ID = "stability.stable-image-ultra-v1:1"
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-west-2")
NUM_IMAGES = 3
BUCKET_NAME = os.environ["STORAGE_BUCKET"]
LOG_TABLE_NAME = os.environ["LOG_TABLE_NAME"]
FONT_KEY = "fonts/Amazon_Ember_Bold.ttf"
tmp_font_path = os.path.join(tempfile.gettempdir(), "test.ttf")

base_size = 2000
circle_tickness = 24
space_between_circle = 170
image_gen_size = 1260
font_size = 120

# Kerning lookup tables for draw_curved_text
KERNING = {
    ('M', 'M'): 60, ('p', 't'): 65, ('S', 'W'): 90, ('r', 'G'): 80,
    ('W', 'A'): 95, ('A', 'W'): 100, ('m', 'm'): 110, ('u', 'm'): 95,
    ('t', 'a'): 60, ('t', 'S'): 60, ('o', 'i'): 60, ('c', 'o'): 65,
    ('k', 'h'): 45, ('e', 'r'): 60, ('a', 't'): 60, ('a', 'l'): 50,
    ('A', 'm'): 85, ('A', 'I'): 70, ('W', 'e'): 90, ('n', 'A'): 80,
}
SINGLE_CHAR_WIDTHS = {'I': 45, 'i': 45, 'm': 80, 'G': 80}

s3_client = boto3.client(
    's3',
    region_name=os.environ.get("AWS_REGION"),
    config=Config(
        signature_version='s3v4',
        s3={'addressing_style': 'virtual'},
    ),
)

s3_client.download_file(BUCKET_NAME, FONT_KEY, tmp_font_path)
FONT = ImageFont.truetype(tmp_font_path, font_size)

bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=BEDROCK_REGION,
    config=Config(read_timeout=300),
)

dynamodb = boto3.resource("dynamodb")
logging_table = dynamodb.Table(LOG_TABLE_NAME)


import re

_MAX_INPUT_LENGTH = 100
_ALLOWED_PATTERN = re.compile(r"^[\w ,.'!\-]+$", re.UNICODE)

def _sanitize_field(value, default):
    """Validate a single input field: must be a string, within length, alphanumeric."""
    if not isinstance(value, str):
        return default
    value = value.strip()
    if not value or len(value) > _MAX_INPUT_LENGTH or not _ALLOWED_PATTERN.match(value):
        return default
    return value


def validate_input(body):
    """Validate and extract input parameters with defaults."""
    logger.info("Validating request input")

    return {
        "animal_name": _sanitize_field(body.get("character"), "panda"),
        "activity": _sanitize_field(body.get("activity"), "dancing"),
        "location": _sanitize_field(body.get("location"), "beach"),
    }


# converting hex colors to rgb tuple
def hex_to_rgb(hex):
    hex = hex.lstrip("#")
    return tuple(int(hex[i: i + 2], 16) for i in (0, 2, 4))


def draw_circle_with_thickness(draw, center, radius, color, thickness):
    """Draw a circle with specified thickness"""
    for i in range(thickness):
        draw.ellipse(
            [
                (center[0] - radius - i, center[1] - radius - i),
                (center[0] + radius + i, center[1] + radius + i),
            ],
            outline=color,
        )


# re-shaping the image from a square into a circle
def overlay_cut(image, h, w):
    # Create a circular mask
    mask = Image.new("L", (h, w), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, h, w), fill=255)

    # Ensure the genimage is in RGBA mode
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Apply the mask
    output = Image.new("RGBA", (h, w), (0, 0, 0, 0))
    output.paste(image, (0, 0), mask)

    return output


def overlay_image(genimage, overlay, h, w):
    # re-shaping the generated image from a square into a circle
    genimage = genimage.resize((h, w))

    # Create a circular mask
    lum_img = Image.new("L", [h, w], 0)
    draw = ImageDraw.Draw(lum_img)
    draw.pieslice([(0, 0), (h, w)], 0, 360, fill=255)
    genimage = genimage.convert('RGB')
    genimage.putalpha(lum_img)
    resizegen = genimage
    # resizegen = text_image.resize((h, w ))

    # overlaying the images
    # resize = overlay.resize((h, w))
    overlay.paste(resizegen, (370, 370), resizegen)

    return overlay


def draw_curved_text(
        draw, text, center, radius, start_angle, text_color, font_size=150, rotation_init=0
):
    """Draw text curved between the circles"""
    font = FONT

    # Calculate text size and spacing
    text_width = sum([font.getlength(letter) for letter in text])
    angular_width = text_width / radius  # Width of text in radians

    # Start position (in radians)
    angle = math.radians(start_angle)
    start_angle_rad = angle - angular_width / 2

    if start_angle == 180 and rotation_init == 180:
        text = text[::-1]

    # Draw each character
    for i in range(len(text)):
        letter = text[i]
        logger.debug(f"text: {text}")
        try:
            logger.debug(f"letter: {letter}, letter + 1 {text[i + 1]}")
            # Calculate letter width and position
            # Check previous char special case
            if i > 0 and letter == 'M' and text[i - 1] == 'M':
                letter_width = 60
            else:
                letter_width = KERNING.get((letter, next_letter := text[i + 1]), SINGLE_CHAR_WIDTHS.get(letter, font.getlength(letter)))
            logger.debug(f"{letter_width} {letter}")

        except IndexError:  # error if th i+1 character doesn't exist
            letter_width = SINGLE_CHAR_WIDTHS.get(letter, font.getlength(letter))
            logger.debug(f"{letter_width} {letter}")

            # letter_angle = letter_width / (2 * radius)

        # Calculate position
        x = center[0] + radius * math.cos(start_angle_rad - math.pi / 2)
        y = center[1] + radius * math.sin(start_angle_rad - math.pi / 2)

        # Calculate rotation angle
        rotation = rotation_init - math.degrees(start_angle_rad)
        # Create rotated text
        txt = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        d.text((50, 50), letter, font=font, fill=text_color, anchor="mm")
        txt = txt.rotate(rotation, expand=True)

        # Paste the letter onto the main image
        draw.paste(txt, (int(x - txt.size[0] / 2), int(y - txt.size[1] / 2)), txt)

        # Move to next letter position
        start_angle_rad += letter_width / radius


def create_overlay(
        genimage,
        top_overlay_prompt="Adopt  AI  2025",
        bottom_overlay_prompt="AWS  -  Grand Palais",
        text_color="#000000",
        circle_color="#000000",
):
    text_color = hex_to_rgb(text_color)
    circle_color = hex_to_rgb(circle_color)

    # Create a base white image
    img1 = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img1)
    # Center point
    center = (base_size / 2, base_size / 2)

    outer_circle_r = base_size - 1200
    inner_circle_r = outer_circle_r - space_between_circle
    # White fill
    draw.ellipse(
        [
            (center[0] - outer_circle_r, center[1] - outer_circle_r),
            (center[0] + outer_circle_r, center[1] + outer_circle_r),
        ],
        fill=(255, 255, 255),
    )
    # Draw circles
    draw_circle_with_thickness(
        draw, center, outer_circle_r, circle_color, circle_tickness + 10
    )  # outer circle
    draw_circle_with_thickness(
        draw, center, inner_circle_r, circle_color, circle_tickness
    )  # inner circle

    # cutting the image to a circle and resizing
    img1 = overlay_cut(img1, base_size, base_size)

    # pasting the overlay image on top of the generated image
    image = overlay_image(genimage, img1, image_gen_size, image_gen_size)

    # Calculate radius for text placement
    # (halfway between inner and outer circles)
    text_radius = (outer_circle_r + inner_circle_r) / 2

    # Add top text
    draw_curved_text(
        draw=image,
        text=top_overlay_prompt,
        center=center,
        radius=text_radius,
        start_angle=0,
        text_color=text_color,
        font_size=font_size,
        rotation_init=0,
    )

    # Add bottom text
    draw_curved_text(
        draw=image,
        text=bottom_overlay_prompt,
        center=center,
        radius=text_radius - 5,
        start_angle=180,
        text_color=text_color,
        font_size=font_size,
        rotation_init=180,
    )

    # Add points
    draw_curved_text(
        draw=image,
        text=".",
        center=center,
        radius=text_radius - 30,
        start_angle=90,
        text_color=text_color,
        font_size=font_size,
        rotation_init=180,
    )
    draw_curved_text(
        draw=image,
        text=".",
        center=center,
        radius=text_radius - 30,
        start_angle=270,
        text_color=text_color,
        font_size=font_size,
        rotation_init=180,
    )

    buffer = io.BytesIO()
    img1.save(buffer, "PNG")
    buffer.seek(0)
    return buffer


# store generated image in s3
def store_in_s3(buffer, s3_object_name, bucket_name, uuid_val):
    # creating s3 resource from the session
    s3_object_name_r = (
        s3_object_name.replace(".", "-").replace(" ", "").replace(":", "-")
    )
    s3_object_name_final = (
            "generated_images/" + str(uuid_val) + "/" + s3_object_name_r + ".png"
    )
    s3_client.upload_fileobj(buffer, bucket_name, s3_object_name_final)
    return s3_object_name_final


def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL for the S3 object"""
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        return None

    return response


def _process_single_image(i, base64_image, request_id):
    """Process a single base64 image: decode, overlay, store in S3, return presigned URL."""
    base64_bytes = base64_image.encode("ascii")
    imagegen = base64.b64decode(base64_bytes)

    image_gen = Image.open(io.BytesIO(imagegen))
    genimage_final_buffer = create_overlay(image_gen)

    object_name = f"image_nb{i}"
    object_name_final = store_in_s3(
        genimage_final_buffer, object_name, BUCKET_NAME, request_id
    )
    logger.debug(f"{object_name_final}")

    return create_presigned_url(BUCKET_NAME, object_name_final)


def _invoke_stability(bedrock_runtime, prompt):
    """Single Stability AI invocation — returns one base64 image."""
    request_body = {
        "prompt": prompt,
        "mode": "text-to-image",
        "aspect_ratio": "1:1",
        "output_format": "png",
        "seed": secrets.randbelow(4294967295),
    }
    response = bedrock_runtime.invoke_model(
        body=json.dumps(request_body),
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )
    response_body = json.loads(response.get("body").read())
    return response_body["images"][0]


def main_bedrock(animal_name, activity, location, request_id):
    # Construct the prompt for cute sticker-like images
    prompt = f"Create a cute sticker-like illustration of a {animal_name} {activity} in {location}. The style should be kawaii, with bright colors, simple shapes, and a cheerful appearance. The animal should be in the middle and small"

    # Stability AI generates one image per call — invoke in parallel for NUM_IMAGES variants
    with ThreadPoolExecutor(max_workers=NUM_IMAGES) as executor:
        base64_images = list(executor.map(
            lambda _: _invoke_stability(bedrock_runtime, prompt),
            range(NUM_IMAGES)
        ))

    # Process all images in parallel
    with ThreadPoolExecutor() as executor:
        all_pre_signed = list(executor.map(
            lambda args: _process_single_image(*args),
            [(i, base64_images[i], request_id) for i in range(len(base64_images))]
        ))
    return all_pre_signed


def log_new_item(request_id, animal, activity, location):
    try:
        logging_table.put_item(
            Item={
                "request_id": request_id,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "animal": animal,
                "activity": activity,
                "location": location,
                "ttl": int((datetime.now() + timedelta(days=30)).timestamp()),
            }
        )
    except Exception as e:
        logger.error(f"Failed to log request {request_id} to DynamoDB: {e}")


def lambda_handler(event, context):
    """Main Lambda function handler."""
    logger.info(f"Received request: httpMethod={event.get('httpMethod')}, path={event.get('path')}")
    try:
        # Extract parameters from the event
        # Parse and validate input
        body = json.loads(event.get("body", "{}"))
        params = validate_input(body)
        animal_name = params.get("animal_name", "friendly cute octopus")
        activity = params.get("activity", "singing with a microphone")
        location = params.get("location", "under the sea")

        request_id = str(uuid.uuid4())
        log_new_item(request_id, animal_name, activity, location)

        all_pre_signed = main_bedrock(animal_name, activity, location, request_id)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
            },
            "body": json.dumps(
                {
                    "presigned": all_pre_signed,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
