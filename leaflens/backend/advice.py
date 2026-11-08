
import os
import time

import requests


API_KEY = os.environ.get("LLM_API_KEY", "")

MODELS = [
    m for m in [
        os.environ.get("LLM_MODEL"),
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-3-flash-preview",
        "gemini-3.5-flash-lite",
    ] if m
]

LANGS = {
    "English": "English",
    "Telugu": "Telugu (తెలుగు)",
    "Hindi": "Hindi (हिन्दी)"
}

_cache = {}


def _prompt(label, crop, lang, weather_note, passages):
    disease = label.replace("_", " ").replace("  ", " ").strip()

    weather_part = ""

    if weather_note:
        weather_part = f"""
Current weather: {weather_note}
Add a short "Weather tip": say whether spread risk is high or low and the best time to spray or avoid spraying. Base it only on the weather given."""

    if passages:
        ref = "\n".join(
            f"[S{i}] {p['text']}"
            for i, p in enumerate(passages, 1)
        )

        chem_rule = f"""Reference passages from official guidelines (text may be jumbled):
{ref}

Rules:
- Use the passages for symptoms and cultural/organic controls. Cite them like [S1].
- For chemicals, name only the general type of product (for example copper-based fungicide). Give NO dose, quantity or concentration, even if a passage shows one.
- Always add: confirm the product and dose with the local agriculture officer or the product label."""

    else:
        chem_rule = """No guideline passage is available.
For chemicals, name only the general type of product.
Give NO dose, quantity or concentration.
Always say to confirm the product and dose with the local agriculture officer or the product label."""

    return f"""You are an agriculture advisor helping a small farmer in Andhra Pradesh, India.

Crop: {crop}
Likely problem (from a photo classifier, may be wrong): {disease}

Reply in {LANGS[lang]}, in simple everyday words, under 220 words, with these short sections:
1. What it is and how to recognise it
2. What to do now (organic and cultural controls first)
3. If chemicals are needed
4. When to get expert help
{weather_part}

{chem_rule}

If the problem is "healthy", say the leaf looks healthy and give 2 prevention tips.
Mention once that the photo check can be wrong."""


def _call(model, prompt):
    url = (
        f"https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    r = requests.post(
        url,
        headers={
            "x-goog-api-key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        },
        timeout=30,
    )

    r.raise_for_status()

    return (
        r.json()["candidates"][0]["content"]["parts"][0]["text"]
        .strip()
    )


def _sources(passages):
    if not passages:
        return ""

    lines = [
        f"[S{i}] {p['source']}, page {p['page']}"
        for i, p in enumerate(passages, 1)
    ]

    return "\n\n**Sources:**\n" + "\n".join(lines)


def get_advice(
    label,
    crop,
    lang="English",
    weather_note="",
    passages=None
):
    passages = passages or []

    key = (
        label,
        crop,
        lang,
        weather_note,
        tuple(
            (p["source"], p["page"])
            for p in passages
        )
    )

    if key in _cache:
        return _cache[key]

    if not API_KEY:
        return (
            "Advice is unavailable right now. "
            "Please ask your local agriculture officer."
        )

    prompt = _prompt(
        label,
        crop,
        lang,
        weather_note,
        passages
    )

    for model in dict.fromkeys(MODELS):
        for attempt in range(2):
            try:
                text = _call(model, prompt) + _sources(passages)

                _cache[key] = text

                return text

            except Exception as e:
                print(
                    f"LLM error ({model}, try {attempt + 1}):",
                    repr(e)
                )

                time.sleep(1.5)

    return (
        "Advice is busy or unavailable right now. "
        "Please try again in a minute, or ask your local agriculture officer."
    )
