# Created by Metrum AI for AMD

from app.providers.base import (
    build_image_prompt_guidance,
    detect_product_vertical,
)


def build_scene_prompt(
    campaign, strategy, market_context: str = ""
) -> tuple[str, str]:
    """Build the system and user prompts for scene prompt generation."""
    system_prompt = """Visual creative director writing prompts for FLUX.1-schnell (text-to-image diffusion model). Output valid JSON:

{"scene_prompts":[
  {"scene_type":"primary","image_prompt":"complete FLUX prompt",
   "video_script":"12-24 word LTX video prompt, or null"},
  {"scene_type":"lifestyle","image_prompt":"...","video_script":"..."},
  {"scene_type":"mood","image_prompt":"...","video_script":"..."}]}

ZERO-TEXT POLICY (OVERRIDES ALL):
The model CANNOT render text. Text is added by a separate compositor.
- NEVER include text, words, letters, numbers, logos, labels, brand names, signage, UI, watermarks in prompts.
- Avoid close-ups of text-bearing surfaces. Use angles/blur/distance to obscure labels.
- End every image_prompt with: "abstract environment only, no people, no product, no text, no lettering, no logos"

NON-HUMAN / NON-PRODUCT POLICY (ALSO OVERRIDES ALL):
- NEVER show people, faces, hands, bodies, silhouettes, or any human subject in generated images.
- NEVER show the product itself, product packaging, product hero shots, devices, bottles, cans, shoes, hardware, or any literal purchasable object.
- Every image must stay abstract, environmental, material-driven, or geometric. Think light, texture, atmosphere, architecture, surfaces, motion, and color -- not subjects.

CAMERA ANGLE FOR COMPOSITION (CRITICAL -- the compositor overlays text on the bottom 35% of every image):
To keep the bottom clear, use LOW CAMERA ANGLES that naturally push subjects to the upper frame:
- "Low angle shot looking upward at..." / "Shot from below, 30-degree upward tilt..."
- "Worm's eye view of..." / "Low perspective looking up toward..."
- NEVER use "eye level", "straight on", or "top down" angles -- they place subjects in the center/bottom.
- NEVER describe what the bottom of the image should contain. Just use camera angles that make the bottom naturally empty (floor, surface, empty space).
- Do NOT write "lower third is gradient" or "bottom is dark" -- the model ignores layout instructions. Only camera angles control where subjects land.

PRODUCT ACCURACY POLICY (CRITICAL):
The image model cannot generate specific product SKUs, model numbers, or niche hardware accurately. A wrong or generic product image is WORSE than no product image at all.
- If the product is a specific SKU (e.g. "AMD RX 7900 XTX", "iPhone 16 Pro", "Nike Air Max 97") do NOT attempt to depict the product itself. The model will generate a wrong-looking version.
- Instead for the PRIMARY scene: create a dramatic, premium environment shot that captures the FEELING of the product category. Use brand colors, dramatic lighting, abstract geometric forms, and material textures that evoke the product's qualities (power, speed, elegance, etc.) WITHOUT showing the product.
- Do NOT depict the product even when it is a simple shape. Keep the image abstract or environmental.
- For LIFESTYLE scenes: express the energy or atmosphere of usage through environment, lighting, motion, and composition only. No humans and no products.

FLUX PROMPT STRUCTURE (35-55 words each, CONCISE):
Subject + composition ("Wide shot of...") > precise lighting > material/texture > depth of field > brand colors > style keywords ("product photography, 8K, shot on Phase One IQ4").
Keep prompts tight. The CLIP encoder truncates at 77 tokens -- front-load the most important visual descriptors.
- Brand colors must be visually dominant in every image. Use them in the lighting, reflections, atmosphere, gradients, and material accents -- not as a minor detail.

VIDEO_SCRIPT: 12-24 words. One camera move + one action + one lighting mood. End with "no text, no logos, no labels, no watermark".

SCENE TYPES (always start with a low-angle camera direction):
- primary: "Low angle shot..." Hero environment. Use abstract geometry with brand palette, dramatic lighting, and premium materials. Never show a person or product.
- lifestyle: "Low angle wide shot..." Usage-adjacent atmosphere expressed through environment, lighting, motion, and spatial cues only. Never show a person or product.
- mood: "Low perspective..." Abstract/conceptual. No literal person or product. Brand palette energy, dramatic upward composition.

RULES: Never say "highlighting"/"emphasizing"/"showcasing". Never reference
invisible specs. Only realistic contexts. Generate exactly 3 scenes."""

    direction = strategy.campaign_direction or ""

    brand_color_info = "Not specified"
    brand_colors = None
    if hasattr(campaign, "brand") and campaign.brand:
        colors = campaign.brand.colors
        if colors:
            brand_colors = colors
            brand_color_info = ", ".join(
                f"{k}: {v}" for k, v in colors.items()
            )

    category_source = " ".join(
        p
        for p in [
            campaign.product_category or "",
            campaign.product_description or "",
        ]
        if p
    ).strip()
    derived_category = campaign.product_category or detect_product_vertical(
        category_source
    )
    visual_guidance = build_image_prompt_guidance(
        product_description=category_source,
        brand_colors=brand_colors,
    )

    user_prompt = f"""Product: {campaign.product_description or 'Not specified'}
Category: {derived_category or 'Not specified'}
Brand Colors: {brand_color_info}
Style: {campaign.style or 'Not specified'}
Tone: {campaign.tone or 'Not specified'}
Creative Direction: {direction}
Visual Vocabulary Anchor: {visual_guidance or 'Use category-appropriate environmental textures and motion.'}

Describe what the camera sees. Keep every image abstract or environmental only.
Do not show any people, body parts, or product objects.
Make the brand palette visually dominant in the final image."""
    if market_context:
        user_prompt += (
            "\n\nOptional market context from live signals "
            "(use only when relevant, do not force weak trends into the creative):\n"
            f"{market_context}"
        )

    return system_prompt, user_prompt


def build_audio_script_prompt(
    campaign, strategy, copy_variants, market_context: str = ""
) -> tuple[str, str]:
    """Build the system and user prompts for audio script generation."""
    system_prompt = """Audio creative director writing 15-second TTS ad scripts. Output valid JSON:

{"audio_scripts":[{"tone":"host_read","script":"full script text","voice":"af_heart","speed":1.0},{"tone":"produced_spot","script":"full script text","voice":"af_heart","speed":1.0}]}

RULES:
- 30-40 words per script. Short sentences (5-10 words). Pauses with periods/dashes.
- Write for the EAR. No URLs, hashtags, or social media references.
- Only reference features from the brief. Do not invent claims.
- NEVER use "game-changer", "revolutionary", "next-gen", or greeting cliches.
- Pick ONE key feature, not a spec list.

TONES:
- host_read: Conversational, genuine excitement. Use "you"/"your".
- produced_spot: Polished, rhythmic. Short declaratives. End on product name.

Generate exactly 2 scripts."""

    headlines = [cv.headline for cv in copy_variants] if copy_variants else []
    direction = strategy.campaign_direction or ""

    user_prompt = f"""Product: {campaign.product_description or 'Not specified'}
Tone: {campaign.tone or 'Not specified'}
Creative Direction: {direction}
Campaign Headlines (for tone reference only, do not repeat them): {headlines}

Write scripts that sound like a real person talking about something they genuinely care about."""
    if market_context:
        user_prompt += (
            "\n\nOptional market context from live signals "
            "(use only when relevant, do not invent claims from it):\n"
            f"{market_context}"
        )

    return system_prompt, user_prompt
