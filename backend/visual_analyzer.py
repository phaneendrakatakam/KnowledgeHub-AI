import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


VISUAL_MODEL = os.getenv(
    "GEMINI_VISUAL_MODEL",
    "gemini-3.1-flash-lite"
)


def _get_client():
    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is required "
            "for multimodal document analysis."
        )

    return genai.Client(
        api_key=api_key
    )


def _clean_json_text(
    text: str
) -> str:
    cleaned = (
        text
        .strip()
    )

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    return cleaned.strip()


def _normalize_visual_type(
    value: str
) -> str:
    normalized = (
        str(
            value or ""
        )
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    aliases = {
        "architecture":
            "architecture_diagram",
        "architecture_diagram":
            "architecture_diagram",
        "flow_chart":
            "flowchart",
        "flowchart":
            "flowchart",
        "chart":
            "chart",
        "graph":
            "chart",
        "screenshot":
            "screenshot",
        "scanned_document":
            "scanned_page",
        "scan":
            "scanned_page",
        "scanned_page":
            "scanned_page",
        "image_with_text":
            "image_with_text",
        "diagram":
            "diagram",
    }

    return aliases.get(
        normalized,
        "other_visual"
    )


def format_visual_evidence(
    analysis: dict
) -> str:
    visual_type = (
        analysis.get(
            "visual_type"
        )
        or "other_visual"
    )

    description = (
        str(
            analysis.get(
                "description",
                ""
            )
        )
        .strip()
    )

    visible_text = (
        analysis.get(
            "visible_text"
        )
        or []
    )

    if isinstance(
        visible_text,
        str
    ):
        visible_text = [
            visible_text
        ]

    visible_text = [
        str(item).strip()
        for item in visible_text
        if str(item).strip()
    ]

    parts = [
        (
            "Visual type: "
            + visual_type.replace(
                "_",
                " "
            )
        )
    ]

    if description:
        parts.append(
            "Description:\n"
            + description
        )

    if visible_text:
        parts.append(
            "Visible text and labels:\n"
            + "\n".join(
                f"- {item}"
                for item
                in visible_text
            )
        )

    return "\n\n".join(
        parts
    ).strip()


def analyze_visual(
    image_bytes: bytes,
    *,
    mime_type: str,
    filename: str,
    page_number: int | None = None,
    section: str | None = None
):
    """
    Analyze a useful document visual and return factual,
    retrieval-friendly evidence.

    Returns None when the model determines that the visual
    does not contain useful knowledge-base information.
    """

    if not image_bytes:
        return None

    location_parts = [
        f"Filename: {filename}"
    ]

    if page_number is not None:
        location_parts.append(
            f"Page: {page_number}"
        )

    if section:
        location_parts.append(
            f"Section: {section}"
        )

    location = " | ".join(
        location_parts
    )

    prompt = f"""
You are analyzing a visual extracted from an enterprise
knowledge document for retrieval-augmented generation.

SOURCE:
{location}

Analyze only information visibly supported by the image.

Useful evidence includes:
- readable text and labels
- architecture components and their connections
- arrows, sequence, workflow and direction
- chart values or comparisons that are visibly shown
- screenshots containing operational or technical information
- scanned document text
- warnings, annotations and callouts

Do not infer hidden facts.
Do not add background knowledge.
Do not describe decorative styling unless it carries meaning.
If the image is only a logo, icon, signature, decorative image,
or otherwise contains no useful knowledge evidence, set
"useful" to false.

Return JSON only in exactly this shape:

{{
  "useful": true,
  "visual_type": "architecture_diagram | flowchart | chart | screenshot | scanned_page | image_with_text | diagram | other_visual",
  "description": "Concise factual description of what the visual proves.",
  "visible_text": ["important visible label or text"]
}}
""".strip()

    client = _get_client()

    response = (
        client.models.generate_content(
            model=VISUAL_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                )
            ]
        )
    )

    raw_text = (
        response.text or ""
    ).strip()

    if not raw_text:
        return None

    try:
        analysis = json.loads(
            _clean_json_text(
                raw_text
            )
        )
    except json.JSONDecodeError:
        return None

    if not analysis.get(
        "useful",
        False
    ):
        return None

    visual_type = (
        _normalize_visual_type(
            analysis.get(
                "visual_type",
                ""
            )
        )
    )

    normalized = {
        "visual_type":
            visual_type,
        "description":
            str(
                analysis.get(
                    "description",
                    ""
                )
            ).strip(),
        "visible_text":
            analysis.get(
                "visible_text"
            )
            or []
    }

    evidence_text = (
        format_visual_evidence(
            normalized
        )
    )

    if not normalized[
        "description"
    ] and not normalized[
        "visible_text"
    ]:
        return None

    normalized[
        "evidence_text"
    ] = evidence_text

    return normalized