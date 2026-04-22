# Created by Metrum AI for AMD

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StrategyResult:
    """Parsed strategy output from the LLM."""

    campaign_direction: str
    audience_segments: list[dict]
    platform_strategy: dict
    track_recommendations: dict
    messaging_angles: list[dict]
    raw_response: dict


@dataclass
class CopyVariantResult:
    """Parsed copy variant from the LLM."""

    framework: str
    headline: str
    body: str
    cta: str
    hashtags: list[str]
    platform_versions: dict


@dataclass
class ScenePromptResult:
    """Parsed scene prompt from the LLM."""

    scene_type: str
    image_prompt: str
    video_script: str | None


@dataclass
class AudioScriptResult:
    """Parsed audio script from the LLM."""

    tone: str
    script: str


@dataclass
class LLMResult:
    """Wraps any LLM call result with audit metadata."""

    data: dict
    raw_request: dict
    raw_response: dict
    model: str
    tokens_used: int | None
    latency_ms: int | None


AD_NEGATIVE_PROMPT = (
    "text, words, letters, numbers, alphabet, characters, typography, "
    "watermark, logo, brand name, product label, signature, stamp, "
    "caption, subtitle, title, heading, writing, font, typed, printed, "
    "inscription, engraving, etching, embossed text, signage, banner text, "
    "person, people, human, face, portrait, body, body part, hand, hands, "
    "model, crowd, character, figure, product, product shot, product photo, "
    "packaging, package, bottle, can, device, hardware, object hero shot, "
    "blurry, low quality, deformed, disfigured, noisy, grainy"
)

# Phrases stripped from prompts before sending to the image model.
# Any prompt fragment that could cause the model to render text is removed.
_TEXT_TRIGGER_PHRASES = [
    "with text",
    "showing text",
    "with the text",
    "with words",
    "showing words",
    "with the word",
    "with the letter",
    "labeled",
    "labelled",
    "that says",
    "that reads",
    "reading",
    "written",
    "spelling",
    "displaying text",
    "with caption",
    "with title",
    "with heading",
    "with logo",
    "with brand",
    "with product name",
    "with watermark",
    "with signature",
]

_IMAGE_THEME_PREFIX = "category anchor:"

NO_TEXT_SUFFIX = (
    ", abstract environment only, no people, no person, no humans, "
    "no faces, no hands, no bodies, no product, no product packaging, "
    "no devices, no product photos, no text, no lettering, no logos"
)

VIDEO_NO_TEXT_SUFFIX = (
    ". no text, no words, no letters, no numbers, no logos, no labels, "
    "no watermark, no subtitles, no captions"
)

_VIDEO_REMOVE_PHRASES = [
    "with text",
    "showing text",
    "with words",
    "with the word",
    "labeled",
    "labelled",
    "that says",
    "that reads",
    "written",
    "with caption",
    "with title",
    "with heading",
    "with logo",
    "with brand",
    "with product name",
    "with watermark",
    "subtitles",
    "captioned",
    "on-screen text",
    "onscreen text",
]


def sanitize_image_prompt(
    raw_prompt: str,
    product_description: str = "",
    brand_colors: dict | None = None,
    scene_type: str = "",
) -> str:
    """Strip any text-triggering language from a prompt and append
    a strict no-text directive. This is the single enforcement point
    for the zero-text-in-generated-images policy."""
    prompt = raw_prompt
    lower = prompt.lower()
    for phrase in _TEXT_TRIGGER_PHRASES:
        idx = lower.find(phrase)
        while idx != -1:
            end = idx + len(phrase)
            prompt = prompt[:idx] + prompt[end:]
            lower = prompt.lower()
            idx = lower.find(phrase)

    # Strip any trailing "no text, no words..." segment the LLM already
    # appended so we don't duplicate it when adding NO_TEXT_SUFFIX.
    lower = prompt.lower()
    for marker in ("no text,", "no text ", "no text."):
        cut = lower.rfind(marker)
        if cut != -1 and cut > len(prompt) * 0.5:
            prompt = prompt[:cut]
            break

    if lower.startswith(_IMAGE_THEME_PREFIX):
        first_sentence = prompt.find(". ")
        if first_sentence != -1:
            prompt = prompt[first_sentence + 2 :]

    theme_guidance = build_image_prompt_guidance(
        product_description=product_description,
        brand_colors=brand_colors,
        scene_type=scene_type,
    )
    if theme_guidance:
        prompt = f"{_IMAGE_THEME_PREFIX} {theme_guidance}. {prompt.lstrip()}"

    prompt = prompt.rstrip(" .,;") + NO_TEXT_SUFFIX
    return prompt


_HEX_COLOR_MAP = {
    "#ed1c24": "red",
    "#ff0000": "red",
    "#cc0000": "dark red",
    "#e91e63": "pink",
    "#ff5722": "orange red",
    "#000000": "black",
    "#333333": "dark gray",
    "#1a1a1a": "black",
    "#ffffff": "white",
    "#f5f5f5": "off-white",
    "#eeeeee": "light gray",
    "#2196f3": "blue",
    "#1976d2": "dark blue",
    "#0d47a1": "navy blue",
    "#4caf50": "green",
    "#388e3c": "dark green",
    "#ffc107": "gold",
    "#ffeb3b": "yellow",
    "#ff9800": "orange",
    "#9c27b0": "purple",
    "#673ab7": "deep purple",
    "#00bcd4": "cyan",
    "#009688": "teal",
}


def _hex_to_color_name(hex_val: str) -> str:
    """Convert a hex color to a descriptive name for prompt injection."""
    h = hex_val.strip().lower()
    if h in _HEX_COLOR_MAP:
        return _HEX_COLOR_MAP[h]
    try:
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    except (ValueError, IndexError):
        return ""
    if r > 180 and g < 80 and b < 80:
        return "red"
    if r > 180 and g > 100 and b < 80:
        return "orange"
    if r > 180 and g > 180 and b < 80:
        return "yellow"
    if r < 80 and g > 150 and b < 80:
        return "green"
    if r < 80 and g < 80 and b > 150:
        return "blue"
    if r > 150 and g < 80 and b > 150:
        return "purple"
    if max(r, g, b) < 50:
        return "black"
    if min(r, g, b) > 200:
        return "white"
    if abs(r - g) < 30 and abs(g - b) < 30:
        return "gray"
    return ""


def _extract_theme_words(raw: str, limit: int = 6) -> str:
    """Pull a few concrete nouns/adjectives from the LLM script."""
    raw = re.sub(r"[^a-zA-Z\s]", " ", raw.lower())
    stop = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "in",
        "on",
        "to",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "that",
        "this",
        "it",
        "its",
        "from",
        "at",
        "by",
        "as",
        "into",
        "has",
        "have",
        "had",
        "not",
        "no",
        "but",
        "if",
        "so",
        "our",
        "we",
        "you",
        "your",
        "their",
        "they",
        "them",
        "will",
        "can",
        "do",
        "does",
        "just",
        "also",
        "very",
        "more",
        "most",
        "new",
        "one",
        "all",
        "each",
        "every",
        "than",
        "up",
        "about",
        "out",
        "over",
        "only",
        "through",
        "between",
        "after",
        "before",
        "while",
        "during",
        "where",
        "how",
        "when",
        "what",
        "which",
        "who",
        "whom",
        "scene",
        "shot",
        "camera",
        "shows",
        "showing",
        "featuring",
        "features",
        "video",
        "clip",
    }
    words = [w for w in raw.split() if len(w) > 2 and w not in stop]
    seen: set[str] = set()
    unique: list[str] = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
        if len(unique) >= limit:
            break
    return ", ".join(unique)


def _brand_color_phrase(brand_colors: dict | None) -> str:
    """Build a strong color directive from brand hex colors."""
    if not brand_colors:
        return ""
    names: list[str] = []
    for key in ("primary", "secondary", "accent"):
        val = brand_colors.get(key, "")
        if isinstance(val, str) and val.startswith("#"):
            name = _hex_to_color_name(val)
            if name and name not in names:
                names.append(name)
    if not names:
        return ""
    return " and ".join(names)


def _image_brand_color_clause(brand_colors: dict | None) -> str:
    """Build a stronger, image-specific palette directive."""
    colors = _brand_color_phrase(brand_colors)
    if not colors:
        return ""
    return (
        f"dominant {colors} palette, {colors} color grading, "
        f"{colors} lighting accents"
    )


_VISUAL_THEMES: list[tuple[list[str], str, dict[str, str]]] = [
    (
        [
            "gpu",
            "graphics",
            "chip",
            "processor",
            "cpu",
            "hardware",
            "compute",
            "semiconductor",
            "silicon",
            "radeon",
            "geforce",
            "nvidia",
            "amd",
            "intel",
        ],
        "gpu hardware",
        {
            "texture": "digital circuit board traces and data grid lines",
            "motion": "pulses of light traveling along circuit paths",
            "feel": "technological and precise",
        },
    ),
    (
        [
            "ai",
            "machine learning",
            "neural",
            "deep learning",
            "model",
            "inference",
            "data",
            "algorithm",
            "automation",
        ],
        "ai software",
        {
            "texture": "neural network nodes connected by glowing synapses",
            "motion": "data particles flowing through interconnected pathways",
            "feel": "intelligent and futuristic",
        },
    ),
    (
        [
            "software",
            "app",
            "platform",
            "saas",
            "cloud",
            "api",
            "developer",
            "code",
            "digital",
            "web",
            "mobile",
        ],
        "software platform",
        {
            "texture": "floating translucent UI panels and holographic grids",
            "motion": "smooth transitions between layered digital surfaces",
            "feel": "clean digital and modern",
        },
    ),
    (
        [
            "food",
            "drink",
            "beverage",
            "coffee",
            "restaurant",
            "snack",
            "organic",
            "recipe",
            "kitchen",
            "flavor",
            "taste",
        ],
        "beverage",
        {
            "texture": "smooth liquid pours and creamy swirls",
            "motion": "slow viscous drips and flowing streams",
            "feel": "warm appetizing and rich",
        },
    ),
    (
        [
            "fashion",
            "clothing",
            "beauty",
            "cosmetic",
            "skincare",
            "luxury",
            "jewelry",
            "perfume",
            "style",
            "designer",
            "wear",
        ],
        "fashion beauty",
        {
            "texture": "flowing silk fabric and shimmering metallic surfaces",
            "motion": "elegant draping cloth ripples in slow motion",
            "feel": "luxurious and refined",
        },
    ),
    (
        [
            "car",
            "auto",
            "vehicle",
            "motor",
            "drive",
            "speed",
            "transport",
            "electric vehicle",
            "ev",
            "racing",
        ],
        "automotive",
        {
            "texture": "aerodynamic speed lines and brushed metal surfaces",
            "motion": "streaking motion blur and wind tunnel light trails",
            "feel": "powerful and dynamic",
        },
    ),
    (
        [
            "finance",
            "bank",
            "invest",
            "insurance",
            "wealth",
            "trading",
            "crypto",
            "payment",
            "fintech",
            "money",
        ],
        "financial services",
        {
            "texture": "clean structured geometric grids and rising bar shapes",
            "motion": "precise ascending lines and expanding concentric rings",
            "feel": "trustworthy and stable",
        },
    ),
    (
        [
            "health",
            "medical",
            "pharma",
            "wellness",
            "fitness",
            "supplement",
            "therapy",
            "care",
            "hospital",
            "biotech",
        ],
        "health wellness",
        {
            "texture": "soft cellular structures and gentle pulse waves",
            "motion": "rhythmic breathing expansion and radial ripples",
            "feel": "clean pure and calming",
        },
    ),
    (
        [
            "music",
            "audio",
            "sound",
            "podcast",
            "streaming",
            "entertainment",
            "gaming",
            "video",
            "media",
            "studio",
        ],
        "media entertainment",
        {
            "texture": "sound wave visualizations and equalizer bar patterns",
            "motion": "rhythmic pulsing beats and vibrating frequency lines",
            "feel": "vibrant and energetic",
        },
    ),
    (
        [
            "sport",
            "athletic",
            "outdoor",
            "adventure",
            "fitness",
            "run",
            "training",
            "gym",
            "performance",
        ],
        "sports fitness",
        {
            "texture": "explosive energy bursts and dynamic motion trails",
            "motion": "fast directional swooshes and impact shock waves",
            "feel": "powerful and high-energy",
        },
    ),
    (
        [
            "eco",
            "green",
            "sustain",
            "solar",
            "renewable",
            "environment",
            "nature",
            "clean energy",
            "recycle",
        ],
        "sustainability",
        {
            "texture": "organic flowing leaf-vein patterns and water ripples",
            "motion": "gentle growth unfurling and natural fluid movement",
            "feel": "natural and harmonious",
        },
    ),
]

_DEFAULT_THEME = {
    "texture": "smooth geometric shapes and flowing light ribbons",
    "motion": "gentle drifting movement and soft particle effects",
    "feel": "modern and professional",
}


def _detect_visual_theme(product_description: str) -> dict[str, str]:
    """Match product description keywords to a visual vocabulary."""
    desc = (product_description or "").lower()
    if not desc:
        return _DEFAULT_THEME
    for keywords, _category, theme in _VISUAL_THEMES:
        for kw in keywords:
            if kw in desc:
                return theme
    return _DEFAULT_THEME


def detect_product_vertical(product_description: str) -> str:
    """Return a broad market/search category using the same mapping as visuals."""
    desc = (product_description or "").lower()
    if not desc:
        return "consumer product"
    for keywords, category, _theme in _VISUAL_THEMES:
        for kw in keywords:
            if kw in desc:
                return category
    return "consumer product"


def build_image_prompt_guidance(
    product_description: str = "",
    brand_colors: dict | None = None,
    scene_type: str = "",
) -> str:
    """Build a deterministic visual-theme anchor for image prompts.

    This keeps the image model tied to the detected category even when
    the LLM prompt drifts into a generic or tech-looking visual language.
    """
    combined = (product_description or "").strip()
    colors = _image_brand_color_clause(brand_colors)
    variant = (scene_type or "").strip().lower()
    if not combined and not colors and not variant:
        return ""

    vertical = (
        detect_product_vertical(combined) if combined else "consumer product"
    )
    vt = _detect_visual_theme(combined)

    parts: list[str] = [vertical]
    if variant:
        parts.append(f"{variant} scene")
    if colors:
        parts.append(colors)

    parts.extend(
        [
            _clip_words(vt["texture"], 8),
            _clip_words(vt["motion"], 7),
            _clip_words(vt["feel"], 5),
        ]
    )
    return ", ".join(p for p in parts if p)


def _is_amd_style_brand(
    brand_name: str, product_description: str, raw_prompt: str
) -> bool:
    """Detect AMD/Radeon/Ryzen campaigns to steer visual style."""
    haystack = " ".join(
        [brand_name or "", product_description or "", raw_prompt or ""]
    ).lower()
    return any(token in haystack for token in ("amd", "radeon", "ryzen"))


def _clip_words(text: str, max_words: int) -> str:
    words = (text or "").split()
    return " ".join(words[:max_words])


def sanitize_video_prompt(
    raw_prompt: str,
    brand_name: str = "",
    brand_colors: dict | None = None,
    scene_type: str = "",
    product_description: str = "",
) -> str:
    """Build a variant-aware abstract animation prompt for AnimateDiff Lightning.

    All variants are abstract -- no objects, no people, no scenes.
    The visual vocabulary (textures, motion style) is derived from the
    product category so a tech ad gets circuit-like patterns, a food ad
    gets liquid flows, etc.

      - primary   : professional, clean, structured
      - lifestyle  : trendy, energetic, dynamic
      - mood       : atmospheric, dreamy, organic
    """
    colors = _brand_color_phrase(brand_colors)
    color_clause = f"{colors} colors, " if colors else ""
    vt = _detect_visual_theme(product_description)
    variant = scene_type.strip().lower()
    amd_style = _is_amd_style_brand(
        brand_name=brand_name,
        product_description=product_description,
        raw_prompt=raw_prompt,
    )

    amd_pattern_clause = ""
    if amd_style:
        vt = {
            "texture": (
                "voxel lattice geometry, triangular tessellation shards, scanline "
                "mesh overlays, reflective metallic planes"
            ),
            "motion": (
                "parallax tunnel drift, forward camera push, volumetric beam "
                "sweeps, pulsing particle field, radial wave propagation"
            ),
            "feel": "premium launch trailer, cinematic industrial precision, "
            "engineered symmetry",
        }
        amd_pattern_clause = (
            "interlocking geometric lattice, angular facet corridors, "
            "concentric tech-ring echoes"
        )
    texture = _clip_words(vt["texture"], 9)
    motion = _clip_words(vt["motion"], 9)
    feel = _clip_words(vt["feel"], 6)

    if variant == "primary":
        parts = [
            f"professional abstract motion graphics, {color_clause}{texture}",
            f"precise controlled motion, {motion}",
            f"dark studio background, {feel}",
            "clean symmetry, polished reflections",
        ]
    elif variant == "lifestyle":
        parts = [
            f"vibrant dynamic abstract animation, {color_clause}bold {texture}",
            f"fast energetic movement, {motion}",
            f"deep dark background with bright accents, {feel}",
            "sharp contrast, cinematic glow, rhythmic pulses",
        ]
    elif variant == "mood":
        parts = [
            f"atmospheric abstract animation, {color_clause}soft flowing {texture}",
            f"gentle slow movement, {motion}",
            "bokeh particles drifting through dark space",
            f"cinematic depth, ethereal, {feel}",
        ]
    else:
        parts = [
            f"abstract motion graphics, {color_clause}{texture}",
            f"{motion}, dark background",
            f"{feel}, gentle organic movement",
        ]

    if amd_pattern_clause:
        if variant == "primary":
            parts.append(f"{amd_pattern_clause}, calibrated structural rhythm")
        elif variant == "lifestyle":
            parts.append(f"{amd_pattern_clause}, energetic impact cadence")
        elif variant == "mood":
            parts.append(f"{amd_pattern_clause}, atmospheric depth layering")
        else:
            parts.append(amd_pattern_clause)

    prompt = ", ".join(parts)
    return prompt + VIDEO_NO_TEXT_SUFFIX


@dataclass
class ImageGenParams:
    """Parameters for image generation inference."""

    width: int = 1088
    height: int = 1344
    num_inference_steps: int = 4
    guidance_scale: float = 0.0
    max_sequence_length: int = 256
    seed: int | None = None
    negative_prompt: str = AD_NEGATIVE_PROMPT


@dataclass
class VideoGenParams:
    """Parameters for video generation inference."""

    width: int = 512
    height: int = 512
    num_frames: int = 32
    num_inference_steps: int = 3
    guidance_scale: float = 1.0
    seed: int | None = None
    fps: int = 8


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | None = None,
    ) -> LLMResult:
        """Send a chat completion request and return the result."""


class ImageProvider(ABC):
    """Abstract base for image generation providers."""

    @abstractmethod
    async def generate_image(
        self, prompt: str, params: ImageGenParams
    ) -> bytes:
        """Generate an image and return raw bytes."""


class TTSProvider(ABC):
    """Abstract base for text-to-speech providers."""

    @abstractmethod
    async def synthesize(
        self, text: str, voice: str = "af_heart", speed: float = 1.0
    ) -> bytes:
        """Synthesize speech and return audio bytes."""


class VideoProvider(ABC):
    """Abstract base for video generation providers."""

    @abstractmethod
    async def generate_video(
        self, prompt: str, params: VideoGenParams
    ) -> bytes:
        """Generate a video clip and return raw bytes."""
