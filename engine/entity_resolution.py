from pathlib import Path
import json
from tqdm import tqdm


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

ENTITIES_FILE = DATA_DIR / "entities.json"


# ============================================================
# LOAD ENTITIES
# ============================================================

with open(
    ENTITIES_FILE,
    "r",
    encoding="utf-8"
) as file:

    entities = json.load(file)


# ============================================================
# CACHE
# ============================================================

_candidates = None


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):
    """Chuan hoa text de entity matching on dinh."""

    if not isinstance(text, str):
        return ""

    text = text.lower().strip()

    text = " ".join(
        text.split()
    )

    return text


# ============================================================
# BUILD CANDIDATES
# ============================================================

def build_candidates(show_progress=False):
    """Build danh sach alias candidates tu entity database."""

    global _candidates

    candidates = []

    items = entities.items()

    if show_progress:

        items = tqdm(
            items,
            total=len(entities),
            desc="Building candidates",
            unit="entity",
            dynamic_ncols=True,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
        )

    for entity_id, entity in items:

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        aliases = entity.get(
            "aliases",
            []
        )

        domains = entity.get(
            "domains",
            []
        )

        sources = entity.get(
            "sources",
            []
        )

        if not isinstance(
            aliases,
            list
        ):
            aliases = []

        # Canonical name luon duoc coi la alias.

        all_aliases = list(
            aliases
        )

        if canonical_name:

            all_aliases.append(
                canonical_name
            )

        # Loai alias trung trong cung entity.

        seen_aliases = set()

        for alias in all_aliases:

            if not isinstance(
                alias,
                str
            ):
                continue

            alias = alias.strip()

            if not alias:
                continue

            normalized_alias = normalize_text(
                alias
            )

            if not normalized_alias:
                continue

            if normalized_alias in seen_aliases:
                continue

            seen_aliases.add(
                normalized_alias
            )

            candidates.append({
                "entity_id": entity_id,
                "canonical_name": canonical_name,
                "alias": alias,
                "normalized_alias": normalized_alias,
                "is_canonical": (
                    normalize_text(
                        canonical_name
                    ) == normalized_alias
                ),
                "domains": domains,
                "sources": sources
            })

    # Alias dai hon duoc uu tien.

    candidates.sort(
        key=lambda item: (
            item["is_canonical"],
            len(item["normalized_alias"])
        ),
        reverse=True
    )

    _candidates = candidates

    return candidates


# ============================================================
# FIND EXACT MATCHES
# ============================================================

def find_exact_matches(
    entity_text,
    entity_type=None
):
    """Tim tat ca exact matches va gom theo entity_id."""

    global _candidates

    normalized_entity = normalize_text(
        entity_text
    )

    if not normalized_entity:
        return []

    if _candidates is None:
        _candidates = build_candidates()

    # Group theo entity_id.
    #
    # Mot entity co nhieu alias giong nhau sau normalize
    # van chi tinh la MOT entity.

    entity_matches = {}

    for candidate in _candidates:

        if candidate["normalized_alias"] != normalized_entity:
            continue

        entity_id = candidate["entity_id"]

        if entity_id not in entity_matches:

            entity_matches[entity_id] = {
                "entity_id": entity_id,
                "canonical_name": candidate[
                    "canonical_name"
                ],
                "matched_alias": candidate[
                    "alias"
                ],
                "domains": candidate[
                    "domains"
                ],
                "sources": candidate[
                    "sources"
                ],
                "is_canonical": candidate[
                    "is_canonical"
                ]
            }

        else:
            # Neu da co canonical match,
            # uu tien canonical name.

            if candidate["is_canonical"]:

                entity_matches[
                    entity_id
                ]["matched_alias"] = candidate[
                    "alias"
                ]

                entity_matches[
                    entity_id
                ]["is_canonical"] = True

    return list(
        entity_matches.values()
    )


# ============================================================
# RESOLVE ONE ENTITY
# ============================================================

def resolve_one_entity(
    entity_text,
    entity_type=None
):
    """Resolve mot entity mention thanh entity chuan."""

    if not entity_text:
        return None

    matches = find_exact_matches(
        entity_text,
        entity_type
    )

    if not matches:
        return None

    # Chi co mot entity thuc su.

    if len(matches) == 1:

        match = matches[0]

        return {
            "mention": entity_text,
            "type": entity_type,
            "entity_id": match["entity_id"],
            "canonical_name": match["canonical_name"],
            "matched_alias": match["matched_alias"],
            "domains": match["domains"],
            "sources": match["sources"]
        }

    # Nhieu entity ID thuc su cung match.

    return {
        "mention": entity_text,
        "type": entity_type,
        "ambiguous": True,
        "candidates": [
            {
                "entity_id": match["entity_id"],
                "canonical_name": match[
                    "canonical_name"
                ],
                "domains": match["domains"]
            }
            for match in matches
        ]
    }


# ============================================================
# ENTITY RESOLUTION
# ============================================================

def resolve_entities(ner_entities):
    """Nhan entity tu NER va resolve thanh canonical entity + ID."""

    if not isinstance(
        ner_entities,
        list
    ):

        return {
            "resolved": [],
            "not_found": [],
            "ambiguous": []
        }

    resolved = []
    not_found = []
    ambiguous = []

    for ner_entity in ner_entities:

        if not isinstance(
            ner_entity,
            dict
        ):
            continue

        entity_text = ner_entity.get(
            "text",
            ""
        )

        entity_type = ner_entity.get(
            "type"
        )

        if not entity_text:
            continue

        # ====================================================
        # EXACT MATCH
        # ====================================================

        matches = find_exact_matches(
            entity_text,
            entity_type
        )

        # ====================================================
        # NOT FOUND
        # ====================================================

        if not matches:

            not_found.append({
                "mention": entity_text,
                "type": entity_type
            })

            continue

        # ====================================================
        # ONE UNIQUE ENTITY
        # ====================================================

        if len(matches) == 1:

            match = matches[0]

            resolved.append({
                "mention": entity_text,
                "type": entity_type,
                "entity_id": match[
                    "entity_id"
                ],
                "canonical_name": match[
                    "canonical_name"
                ],
                "matched_alias": match[
                    "matched_alias"
                ],
                "domains": match[
                    "domains"
                ],
                "sources": match[
                    "sources"
                ]
            })

            continue

        # ====================================================
        # REAL AMBIGUOUS
        # ====================================================

        ambiguous.append({
            "mention": entity_text,
            "type": entity_type,
            "candidates": [
                {
                    "entity_id": match[
                        "entity_id"
                    ],
                    "canonical_name": match[
                        "canonical_name"
                    ],
                    "domains": match[
                        "domains"
                    ]
                }
                for match in matches
            ]
        })

    return {
        "resolved": resolved,
        "not_found": not_found,
        "ambiguous": ambiguous
    }


# ============================================================
# DISPLAY TEST
# ============================================================

def display_resolution(result):
    """Hien ket qua Entity Resolution."""

    print()

    print(
        "Resolved:",
        len(result["resolved"])
    )

    for entity in result["resolved"]:

        print(
            " ",
            entity["mention"],
            "->",
            entity["canonical_name"],
            "->",
            entity["entity_id"]
        )

    print(
        "Not found:",
        len(result["not_found"])
    )

    for entity in result["not_found"]:

        print(
            " ",
            entity["mention"]
        )

    print(
        "Ambiguous:",
        len(result["ambiguous"])
    )

    for entity in result["ambiguous"]:

        print(
            " ",
            entity["mention"],
            "->",
            [
                candidate["canonical_name"]
                for candidate in entity[
                    "candidates"
                ]
            ]
        )


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    build_candidates(
        show_progress=True
    )

    print(
        "Entity Resolution is running..."
    )

    print(
        "Candidates:",
        len(_candidates)
    )