# Created by Metrum AI for AMD


def build_strategy_prompt(
    campaign, market_context: str = ""
) -> tuple[str, str]:
    """Build the system and user prompts for strategy generation."""
    system_prompt = """Senior advertising strategist. Output valid JSON:

{"campaign_direction":"1-2 sentence creative thesis -- a human truth, not a product description",
"audience_segments":[{"name":"specific","demographics":"age/gender/income/psychographics","platforms":"2-3 platforms","rationale":"why this segment for THIS product"}],
"platform_strategy":{"youtube":"strategy","reddit":"strategy","instagram":"strategy"},
"track_recommendations":{"image_text":{"recommended":true,"rationale":"why"},"audio_podcast":{"recommended":true,"rationale":"why"},"video":{"recommended":false,"rationale":"why"}},
"messaging_angles":[{"angle":"name","description":"emotional connection to audience"}]}

RULES:
- campaign_direction = customer INSIGHT, not product description.
- 3 DISTINCT audience segments, 3 messaging angles.
- messaging_angles must connect EMOTIONALLY.
- track_recommendations must be driven by audience-channel fit, not generic defaults.
- Do NOT recommend every track by default. Recommend only tracks with clear fit.
- Use ONLY information from the brief. Do NOT invent features or contexts."""

    user_prompt = f"""Campaign Brief:
- Product: {campaign.product_description or 'Not specified'}
- Category: {campaign.product_category or 'Not specified'}
- Objective: {campaign.objective or 'Not specified'}
- Style: {campaign.style or 'Not specified'}
- Tone: {campaign.tone or 'Not specified'}
- Target Audience: {campaign.target_audience or 'Determine the best segments based on the product and objective'}

Base your entire strategy on the information above.
Do not assume or invent details about the product that are not in the brief."""
    if market_context:
        user_prompt += (
            "\n\nOptional market context from live signals "
            "(use only when relevant, do not turn it into unsupported claims). "
            "Use any track-fit summary here directly when deciding track_recommendations:\n"
            f"{market_context}"
        )

    return system_prompt, user_prompt


def strategy_response_format() -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "strategy",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "campaign_direction",
                    "audience_segments",
                    "platform_strategy",
                    "track_recommendations",
                    "messaging_angles",
                ],
                "properties": {
                    "campaign_direction": {"type": "string"},
                    "audience_segments": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "name",
                                "demographics",
                                "platforms",
                                "rationale",
                            ],
                            "properties": {
                                "name": {"type": "string"},
                                "demographics": {"type": "string"},
                                "platforms": {"type": "string"},
                                "rationale": {"type": "string"},
                            },
                        },
                    },
                    "platform_strategy": {"type": "object"},
                    "track_recommendations": {"type": "object"},
                    "messaging_angles": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["angle", "description"],
                            "properties": {
                                "angle": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    }
