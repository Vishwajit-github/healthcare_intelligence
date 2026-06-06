import base64
import mimetypes
import os
from pathlib import Path
from typing import Optional, Union

import requests
from dotenv import load_dotenv
from openai import OpenAI
from config import openai_client

DEFAULT_MODEL="gpt-5.1"
# =========================================================
# HELPERS
# =========================================================

def _bytes_to_data_url(
    image_bytes: bytes,
    mime_type: str,
) -> str:

    encoded_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return (
        f"data:{mime_type};base64,{encoded_image}"
    )


def _load_image_path_as_data_url(
    image_path: Union[str, Path, bytes],
    mime_type: Optional[str] = None,
) -> str:

    # =====================================================
    # RAW BYTES
    # =====================================================

    if isinstance(image_path, bytes):

        return _bytes_to_data_url(
            image_path,
            mime_type or DEFAULT_MIME_TYPE,
        )

    image_reference = str(image_path).strip()

    # =====================================================
    # URL IMAGE
    # =====================================================

    if image_reference.startswith(
        ("http://", "https://")
    ):

        response = requests.get(
            image_reference,
            timeout=30,
        )

        response.raise_for_status()

        detected_mime_type = (
            mime_type
            or response.headers.get(
                "content-type",
                "",
            ).split(";")[0]
            or DEFAULT_MIME_TYPE
        )

        return _bytes_to_data_url(
            response.content,
            detected_mime_type,
        )

    # =====================================================
    # LOCAL FILE PATH
    # =====================================================

    resolved_image_path = (
        Path(image_reference)
        .expanduser()
        .resolve()
    )

    if not resolved_image_path.exists():

        raise FileNotFoundError(
            f"Image file not found: {resolved_image_path}"
        )

    detected_mime_type = (
        mime_type
        or mimetypes.guess_type(
            str(resolved_image_path)
        )[0]
        or DEFAULT_MIME_TYPE
    )

    image_bytes = resolved_image_path.read_bytes()

    return _bytes_to_data_url(
        image_bytes,
        detected_mime_type,
    )


# =========================================================
# MAIN TOOL
# =========================================================

def medical_imaging_analysis_tool_(
    image_path: Union[str, Path, bytes],
    user_query: str = "",
    mime_type: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> str:

    """
    Analyze medical images using OpenAI Vision.

    Supports:
    - Local image paths
    - Image URLs
    - Raw image bytes

    Medical image types:
    - Prescription photos
    - X-rays
    - CT scans
    - MRI
    - Ultrasound
    - PET scans
    - Dermatology images
    - Lab report screenshots
    - Clinical photographs
    """

    # =====================================================
    # VALIDATION
    # =====================================================

    if not image_path:

        return "Error: image_path is required."

    question = (
        user_query.strip()
        or "Analyze this medical image."
    )

    try:

        print("\n🧠 MEDICAL IMAGING TOOL")
        print(f"Image Path: {image_path}")
        print(f"Question: {question}")

        # =================================================
        # LOAD IMAGE
        # =================================================

        image_data_url = _load_image_path_as_data_url(
            image_path=image_path,
            mime_type=mime_type,
        )

        # =================================================
        # MULTIMODAL MESSAGES
        # =================================================

        messages = [

            {
                "role": "system",
                "content": """
You are a Medical Imaging Analysis Assistant.

You can analyze:
- prescriptions
- medicine names
- x-rays
- CT scans
- MRI scans
- ultrasound
- radiology images
- dermatology images
- lab reports
- clinical photographs

Rules:
- Never hallucinate unreadable text.
- Mention uncertainty clearly.
- Use cautious medical language.
- Do not provide final diagnosis.
- Do not prescribe medications.
- Stay grounded in visible image content.
"""
            },

            {
                "role": "user",
                "content": [

                    {
                        "type": "text",
                        "text": question,
                    },

                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        },
                    },
                ],
            },
        ]

        # =================================================
        # OPENAI VISION CALL
        # =================================================

        response = openai_client.chat.completions.create(

            model=model,

            messages=messages,

            max_completion_tokens=2000,
        )

        final_output = (
            response
            .choices[0]
            .message
            .content
        )

        print("\n✅ MEDICAL IMAGING OUTPUT:")
        print(final_output)

        return final_output or ""

    except Exception as exc:

        print("\n❌ MEDICAL IMAGING ERROR")
        print(exc)

        return (
            f"Error analyzing medical image: {exc}"
        )