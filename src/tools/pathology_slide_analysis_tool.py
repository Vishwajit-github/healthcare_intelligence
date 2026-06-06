import base64
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Union
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path(__file__).resolve().parents[2] / ".env.example")

DEFAULT_MODEL = "gpt-5.4-mini"
SUPPORTED_WSI_EXTENSIONS = {".svs", ".tif", ".tiff"}
THUMBNAIL_MIME_TYPE = "image/jpeg"


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _bytes_to_data_url(image_bytes: bytes, mime_type: str = THUMBNAIL_MIME_TYPE) -> str:
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded_image}"


def _get_url_suffix(slide_url: str) -> str:
    suffix = Path(urlparse(slide_url).path).suffix.lower()
    return suffix if suffix in SUPPORTED_WSI_EXTENSIONS else ".tiff"


def _download_slide_to_tempfile(slide_url: str) -> Path:
    response = requests.get(slide_url, timeout=120)
    response.raise_for_status()

    temp_file = tempfile.NamedTemporaryFile(
        suffix=_get_url_suffix(slide_url),
        delete=False,
    )
    temp_file.write(response.content)
    temp_file.close()
    return Path(temp_file.name)


def _render_with_openslide(slide_path: Path, max_size: int) -> Tuple[bytes, str]:
    try:
        import openslide
    except ImportError as exc:
        raise RuntimeError(
            "OpenSlide is required for .svs whole slide images. Install openslide-python "
            "and the OpenSlide native library, or provide a supported TIFF preview."
        ) from exc

    with openslide.OpenSlide(str(slide_path)) as slide:
        thumbnail = slide.get_thumbnail((max_size, max_size)).convert("RGB")
        dimensions = f"{slide.dimensions[0]} x {slide.dimensions[1]} pixels"

    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_image:
        thumbnail.save(temp_image.name, format="JPEG", quality=90)
        temp_image.seek(0)
        return temp_image.read(), dimensions


def _render_with_pillow(slide_path: Path, max_size: int) -> Tuple[bytes, str]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required to render TIFF whole slide images.") from exc

    Image.MAX_IMAGE_PIXELS = None

    with Image.open(slide_path) as image:
        dimensions = f"{image.width} x {image.height} pixels"
        image.thumbnail((max_size, max_size))
        thumbnail = image.convert("RGB")

    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_image:
        thumbnail.save(temp_image.name, format="JPEG", quality=90)
        temp_image.seek(0)
        return temp_image.read(), dimensions


def _render_wsi_preview(
    slide_image: Union[str, Path],
    max_thumbnail_size: int,
) -> Tuple[str, str, str]:
    slide_reference = str(slide_image)
    temp_slide_path: Optional[Path] = None

    try:
        if slide_reference.startswith(("http://", "https://")):
            slide_path = _download_slide_to_tempfile(slide_reference)
            temp_slide_path = slide_path
        else:
            slide_path = Path(slide_reference).expanduser()

        if not slide_path.exists():
            raise FileNotFoundError(f"Slide image not found: {slide_path}")

        extension = slide_path.suffix.lower()
        if extension not in SUPPORTED_WSI_EXTENSIONS:
            raise ValueError(
                "Unsupported pathology slide format. Expected .svs, .tif, or .tiff."
            )

        if extension == ".svs":
            thumbnail_bytes, dimensions = _render_with_openslide(
                slide_path,
                max_thumbnail_size,
            )
        else:
            try:
                thumbnail_bytes, dimensions = _render_with_pillow(
                    slide_path,
                    max_thumbnail_size,
                )
            except Exception:
                thumbnail_bytes, dimensions = _render_with_openslide(
                    slide_path,
                    max_thumbnail_size,
                )

        return _bytes_to_data_url(thumbnail_bytes), dimensions, extension

    finally:
        if temp_slide_path and temp_slide_path.exists():
            temp_slide_path.unlink()


def pathology_slide_analysis_tool(
    slide_image: Union[str, Path],
    user_query: str = "",
    model: str = DEFAULT_MODEL,
    max_thumbnail_size: int = 1800,
) -> str:
    """
    Analyze a whole slide pathology image preview and answer a pathology query.

    Args:
        slide_image: Local path or URL for a .svs, .tif, or .tiff whole slide image.
        user_query: User's pathology question about the slide.
        model: OpenAI vision-capable model name.
        max_thumbnail_size: Maximum width/height for the generated WSI preview.

    Returns:
        A structured pathology slide analysis response.
    """
    if not slide_image:
        return "Error: slide_image input is required."

    question = user_query.strip() or (
        "Analyze this whole slide pathology image and summarize the key findings."
    )

    try:
        preview_data_url, dimensions, extension = _render_wsi_preview(
            slide_image,
            max_thumbnail_size=max_thumbnail_size,
        )

        messages = [
            {
                "role": "system",
                "content": """
You are a pathology slide analysis assistant.

Analyze the provided whole slide image preview and respond to the user's query.
Be clinically cautious and do not present the response as a final diagnosis.
This preview may not show all high-power microscopic details from the original
WSI, so clearly state limitations and recommend review by a board-certified
pathologist when needed.

Return:
1. Slide overview
2. Tissue adequacy and quality notes
3. Key visible histopathology findings
4. Suspicious or abnormal regions, if visible
5. Impression or differential considerations
6. Direct answer to the user query
7. Recommended next review steps
8. Limitations of preview-based WSI analysis
""",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"{question}\n\n"
                            f"Slide format: {extension}\n"
                            f"Original slide dimensions: {dimensions}\n"
                            "The attached image is a generated low-power preview "
                            "of the whole slide image."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": preview_data_url}},
                ],
            },
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=3500,
        )

        return response.choices[0].message.content or ""

    except Exception as exc:
        return f"Error analyzing pathology slide: {exc}"
