"""Generate eBay-style listings from rough estate/vintage jewelry notes."""

import html
import re

# eBay title limit
TITLE_MAX = 80

# Item-type keyword -> (display name, category hint)
_ITEM_TYPES = [
    (r"rope\s*chain", "Rope Chain Necklace",
     "Jewelry & Watches > Fine Jewelry > Fine Necklaces & Pendants > Chains"),
    (r"\bchain\b|\bnecklace\b|\bpendant\b|\blocket\b", "Necklace",
     "Jewelry & Watches > Fine Jewelry > Fine Necklaces & Pendants"),
    (r"\bring\b", "Ring",
     "Jewelry & Watches > Fine Jewelry > Fine Rings"),
    (r"\bbangle\b|\bb illumination\b|\bbracelet\b|\bcuff\b", "Bracelet",
     "Jewelry & Watches > Fine Jewelry > Fine Bracelets"),
    (r"\bearring|studs?|hoops?|dangle|drop\b", "Earrings",
     "Jewelry & Watches > Fine Jewelry > Fine Earrings"),
    (r"\bbrooch\b|\bpin\b|cameo\b", "Brooch",
     "Jewelry & Watches > Vintage & Antique Jewelry > Brooches & Pins"),
    (r"\bwatch\b", "Watch",
     "Jewelry & Watches > Watches, Parts & Accessories > Watches"),
    (r"\bcharm\b", "Charm",
     "Jewelry & Watches > Fashion Jewelry > Charms & Pendants"),
]

_METALS = [
    ("yellow gold", "Yellow Gold"),
    ("rose gold", "Rose Gold"),
    ("white gold", "White Gold"),
    ("gold filled", "Gold Filled"),
    ("gold vermeil", "Gold Vermeil"),
    ("gold", "Gold"),
    ("platinum", "Platinum"),
    ("sterling silver", "Sterling Silver"),
    ("sterling", "Sterling Silver"),
    ("silver", "Silver"),
    ("rhodium", "Rhodium"),
]

_STONES = [
    "diamond", "ruby", "sapphire", "emerald", "opal", "pearl",
    "amethyst", "topaz", "garnet", "turquoise", "onyx", "jade",
    "cubic zirconia", "cz", "crystal", "rhinestone", "coral",
]

_STYLES = ["art deco", "art nouveau", "victorian", "edwardian",
           "retro", "mid-century", "vintage", "antique", "estate"]


def _extract(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(0) if m else None


def _detect_karat(text: str) -> str | None:
    m = re.search(r"(10|14|18|22|24)\s?[kK](?:arat)?\b", text)
    if m:
        return f"{m.group(1)}K"
    m = re.search(r"\b(925|800|585|750)\b", text)
    if m:
        return {"925": "925 (Sterling)", "585": "14K",
                "750": "18K", "800": "800 Silver"}.get(m.group(1), m.group(1))
    if re.search(r"sterling|925", text, re.IGNORECASE):
        return "925 (Sterling)"
    return None


def _detect_metal(text: str) -> str | None:
    low = text.lower()
    for key, label in _METALS:
        if key in low:
            return label
    return None


def _detect_item_type(text: str) -> tuple[str, str]:
    for pattern, name, category in _ITEM_TYPES:
        if re.search(pattern, text, re.IGNORECASE):
            # Preserve style qualifiers like "Rope Chain"
            return name, category
    return "Jewelry", "Jewelry & Watches > Vintage & Antique Jewelry"


def _detect_length(text: str) -> str | None:
    m = re.search(r'(\d+(?:\.\d+)?)\s?(inch|in|"|mm|cm)\b', text, re.IGNORECASE)
    if m:
        val, unit = m.group(1), m.group(2).lower()
        if unit in ("inch", "in", '"'):
            return f"{val} inch"
        return f"{val} {unit}"
    return None


def _detect_weight(text: str) -> str | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s?(g|grams?|dwt|pennyweight|oz)\b",
                  text, re.IGNORECASE)
    if m:
        val, unit = m.group(1), m.group(2).lower()
        if unit.startswith("gram"):
            unit = "g"
        return f"{val}{unit}" if unit == "g" else f"{val} {unit}"
    return None


def _detect_clasp(text: str) -> str | None:
    for clasp in ["lobster clasp", "spring ring", "box clasp",
                  "toggle clasp", "hook clasp", "magnetic clasp"]:
        if clasp in text.lower():
            return " ".join(w.capitalize() for w in clasp.split())
    return None


def _detect_stones(text: str) -> list[str]:
    low = text.lower()
    found = [s.title() if s != "cz" else "CZ" for s in _STONES if s in low]
    if re.search(r"no stones?|without stones?|no gem", low):
        return []
    return found


def _detect_era(text: str) -> str | None:
    low = text.lower()
    for style in _STYLES:
        if style in low:
            return style.title() if style != "mid-century" else "Mid-Century"
    return None


def _condition_notes(text: str) -> str:
    low = text.lower()
    notes = []
    if "light polish wear" in low or "wear" in low:
        notes.append("light polish wear consistent with age")
    if "patina" in low:
        notes.append("lovely age patina")
    if re.search(r"\bgood\b|\bvery good\b|\bexcellent\b", low):
        m = re.search(r"(very good|excellent|good)\s*(condition|estate condition)?",
                       low)
        if m:
            notes.append(f"{m.group(1).strip()} estate condition")
    if re.search(r"no stones?|no gem", low):
        notes.append("no stones")
    if not notes:
        notes.append("estate condition — please review photos")
    return "; ".join(notes)


def generate_listing(notes: str) -> dict:
    """Turn rough jewelry notes into an eBay-ready listing pack.

    Args:
        notes: Free-form seller notes, e.g.
            "14k yellow gold rope chain, 18 inch, 3.2g, ..."

    Returns:
        dict with keys: title, description, item_specifics, tags,
        category_hint.
    """
    raw = (notes or "").strip()
    if not raw:
        raise ValueError("notes must be a non-empty string")

    karat = _detect_karat(raw)
    metal = _detect_metal(raw)
    item_name, category = _detect_item_type(raw)
    length = _detect_length(raw)
    weight = _detect_weight(raw)
    clasp = _detect_clasp(raw)
    stones = _detect_stones(raw)
    era = _detect_era(raw) or "Estate"
    condition = _condition_notes(raw)

    marked = _extract(
        r"marked\s+[^,.;]+|stamped\s+[^,.;]+|signed\s+[^,.;]+", raw)
    origin = None
    for place in ["Italy", "France", "Mexico", "England", "USA", "Japan"]:
        if re.search(rf"\b{place}\b", raw, re.IGNORECASE):
            origin = place
            break

    # ---- Title (eBay style, <= 80 chars) ----
    parts: list[str] = []
    if karat and "sterling" not in karat.lower():
        parts.append(karat.upper() if re.match(r"\d+K$", karat) else karat)
    if metal:
        parts.append(metal)
    if "Chain" not in item_name and re.search(r"chain", raw, re.IGNORECASE):
        style_bit = "Rope Chain" if re.search(r"rope", raw, re.IGNORECASE) \
            else "Chain"
        parts.append(f"{style_bit} {item_name}")
    else:
        parts.append(item_name)
    if length:
        parts.append(length.replace(" inch", '"').replace("inch", '"'))
    if weight:
        parts.append(weight)
    if era and era.lower() not in " ".join(parts).lower():
        parts.append(era)
    if origin and origin.lower() not in " ".join(parts).lower():
        parts.append(origin)

    title = " ".join(parts)
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) > TITLE_MAX:
        # Drop trailing qualifiers first to fit
        while len(title) > TITLE_MAX and len(parts) > 2:
            parts.pop()
            title = " ".join(parts)
        title = title[:TITLE_MAX].rstrip()

    # ---- Description (HTML-safe paragraphs) ----
    metal_phrase = " ".join(p for p in [karat, metal] if p) or "estate metal"
    para1 = (f"Offered here is a lovely estate {metal_phrase.lower()} "
             f"{item_name.lower()}. {raw.strip().rstrip('.')}.")
    details = []
    if length:
        details.append(f"Length: {length}")
    if weight:
        details.append(f"Weight: {weight}")
    if clasp:
        details.append(f"Closure: {clasp}")
    if stones:
        details.append(f"Stones: {', '.join(stones)}")
    if marked:
        details.append(marked.strip().capitalize())
    para2 = " ".join(details) if details else "See photos for details."
    para3 = (f"Condition: {condition}. Estate/vintage piece sold as-is; "
             "please examine all photos and ask questions before buying.")

    paragraphs = [para1, para2, para3]
    description = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)

    # ---- Item specifics ----
    item_specifics: dict = {
        "Type": item_name,
        "Style": era,
        "Condition": "Pre-Owned",
    }
    if metal:
        item_specifics["Metal"] = metal
    if karat:
        item_specifics["Metal Purity"] = karat
    if length:
        item_specifics["Length"] = length
    if weight:
        item_specifics["Weight"] = weight
    if clasp:
        item_specifics["Closure"] = clasp
    if stones:
        item_specifics["Main Stone"] = ", ".join(stones)
    if origin:
        item_specifics["Country of Origin"] = origin
    if marked:
        item_specifics["Marks"] = marked.strip()

    # ---- Tags ----
    tags: list[str] = []
    for bit in [karat, metal, item_name, era, origin, clasp]:
        if bit:
            tags.append(bit.lower())
    if length:
        tags.append(length.lower())
    if re.search(r"rope", raw, re.IGNORECASE):
        tags.append("rope chain")
    tags.append("estate jewelry")
    tags.append("vintage jewelry")
    # de-dupe, preserve order
    seen: set = set()
    deduped = [t for t in tags if not (t in seen or seen.add(t))]
    tags = deduped

    return {
        "title": title,
        "description": description,
        "item_specifics": item_specifics,
        "tags": tags,
        "category_hint": category,
    }
