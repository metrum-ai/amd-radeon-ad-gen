# Created by Metrum AI for AMD


def build_copy_prompt(
    campaign, strategy, market_context: str = ""
) -> tuple[str, str]:
    """Build the system and user prompts for copy variant generation."""
    system_prompt = """Elite copywriter. Output valid JSON:

{"copy_variants":[{"framework":"AIDA","headline":"max 50 chars","body":"max 120 chars","cta":"max 25 chars, action verb + outcome","hashtags":["3-4 hashtags"],"platform_versions":{"meta":{"headline":"max 40 chars","body":"max 125 chars"},"google_ads":{"headline":"max 30 chars","description":"max 90 chars"},"linkedin":{"headline":"max 70 chars","body":"max 150 chars"}}}]}

MANDATORY: You MUST return EXACTLY 3 copy variants in the copy_variants array. No more, no less.

FRAMEWORKS (one variant each, all 3 are REQUIRED):
1. AIDA: Bold hook, ONE proof point, desired outcome, drive action.
2. PAS: Specific pain, what it COSTS them, product as fix.
3. BAB: Vivid "before", tangible "after", product bridges.

RULES:
- Headlines stop mid-scroll. No colons, no feature lists.
- CTAs: specific outcome, no exclamation marks. Never "Learn More"/"Shop Now".
- NEVER use: "Unleash", "Unlock", "Experience", "Discover", "Revolutionary", "Game-changer".
- Use ONLY product details from the brief. Do not invent claims."""

    direction = strategy.campaign_direction or ""
    segments = strategy.audience_segments or []

    user_prompt = f"""Product: {campaign.product_description or 'Not specified'}
Objective: {campaign.objective or 'Not specified'}
Tone: {campaign.tone or 'Not specified'}
Creative Direction: {direction}
Primary Audience: {segments[0] if segments else 'Not specified'}

Write copy that makes someone who has never heard of this product stop and read.
Use ONLY product details from the brief above."""
    if market_context:
        user_prompt += (
            "\n\nOptional market context from live signals "
            "(use only when relevant, do not create unsupported claims):\n"
            f"{market_context}"
        )

    return system_prompt, user_prompt


def copy_response_format() -> dict:
    """JSON schema enforcement for OpenAI-compatible response_format."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "copy_gen",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["copy_variants"],
                "properties": {
                    "copy_variants": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "framework",
                                "headline",
                                "body",
                                "cta",
                                "hashtags",
                                "platform_versions",
                            ],
                            "properties": {
                                "framework": {
                                    "type": "string",
                                    "enum": ["AIDA", "PAS", "BAB"],
                                },
                                "headline": {"type": "string"},
                                "body": {"type": "string"},
                                "cta": {"type": "string"},
                                "hashtags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                },
                                "platform_versions": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": [
                                        "meta",
                                        "google_ads",
                                        "linkedin",
                                    ],
                                    "properties": {
                                        "meta": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": ["headline", "body"],
                                            "properties": {
                                                "headline": {"type": "string"},
                                                "body": {"type": "string"},
                                            },
                                        },
                                        "google_ads": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": [
                                                "headline",
                                                "description",
                                            ],
                                            "properties": {
                                                "headline": {"type": "string"},
                                                "description": {
                                                    "type": "string"
                                                },
                                            },
                                        },
                                        "linkedin": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": ["headline", "body"],
                                            "properties": {
                                                "headline": {"type": "string"},
                                                "body": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    }
                },
            },
        },
    }
