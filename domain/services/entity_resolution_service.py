"""Entity Resolution and Multi-Signal Matching Engine for Sanctions Screening.

Features:
- Cross-lingual Arabic & English text normalization.
- Tashkeel (diacritics) stripping, Hamza unification, Taa Marbuta / Alif Maqsura normalization.
- Transliteration equivalence and token alignment.
- Multi-signal scoring combining:
  1. Primary and alias name similarity (Jaro-Winkler, Levenshtein, Token Sort)
  2. Date of birth exact / fuzzy match and conflict penalty
  3. Country / nationality match and conflict penalty
  4. Identifier (National ID, Tax ID, Passport) agreement
- Transparent, explainable breakdown (matched fields, conflicting fields, missing fields, narrative reasoning).
- Human-in-the-Loop decision recommendations.
"""

from __future__ import annotations

import difflib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Arabic Tashkeel (diacritics) + Tatweel
_TASHKEEL_REGEX = re.compile(r"[\u064B-\u065F\u0670\u0640]")

# Arabic Hamza forms to normalize to bare Alif (ا)
_HAMZA_MAP = {
    "\u0622": "\u0627",  # آ -> ا
    "\u0623": "\u0627",  # أ -> ا
    "\u0625": "\u0627",  # إ -> ا
    "\u0671": "\u0627",  # ٱ -> ا
}

# Arabic orthographic variants
_CHAR_MAP = {
    "\u0629": "\u0647",  # ة -> ه
    "\u0649": "\u064A",  # ى -> ي
}

# Common transliteration synonym clusters
_TRANSLITERATION_SYNONYMS: dict[str, str] = {
    "muhammad": "mohamed",
    "mohammed": "mohamed",
    "mohammad": "mohamed",
    "mahmoud": "mohamed",
    "ahmad": "ahmed",
    "usama": "osama",
    "tareq": "tariq",
    "tarek": "tariq",
    "abdul": "abdel",
    "abd": "abdel",
    "hussain": "hussein",
    "hasan": "hassan",
    "sayyed": "sayed",
    "alsayed": "sayed",
    "elsayed": "sayed",
}

_HONORIFICS_REGEX = re.compile(
    r"\b(mr|mrs|ms|dr|eng|sheikh|general|admiral|haji|al-hajj|colonel|sir)\b\.?",
    re.IGNORECASE,
)


def normalize_arabic_text(text: str) -> str:
    """Normalize Arabic script text by stripping diacritics and unifying character forms."""
    if not text:
        return ""

    # 1. Strip Tashkeel & Tatweel
    s = _TASHKEEL_REGEX.sub("", text)

    # 2. Normalize Hamzas
    for k, v in _HAMZA_MAP.items():
        s = s.replace(k, v)

    # 3. Normalize Taa Marbuta & Alif Maqsura
    for k, v in _CHAR_MAP.items():
        s = s.replace(k, v)

    # 4. Remove leading Arabic definite article 'ال' from words
    words = s.split()
    normalized_words = []
    for w in words:
        if w.startswith("ال") and len(w) > 3:
            normalized_words.append(w[2:])
        else:
            normalized_words.append(w)

    return " ".join(normalized_words).strip()


def normalize_english_text(text: str) -> str:
    """Normalize Latin script text by removing punctuation, honorifics, and standardizing prefixes."""
    if not text:
        return ""

    s = text.lower()

    # Strip honorifics
    s = _HONORIFICS_REGEX.sub("", s)

    # Standardize and strip prefixes like al-, el-, abdel-, abdul-
    s = re.sub(r"\b(al|el)[\s\-]+", " ", s)
    s = re.sub(r"\b(abdel|abdul)[\s\-]+", "abdel ", s)

    # Remove non-alphanumeric chars (keep spaces)
    s = re.sub(r"[^\w\s]", " ", s)

    # Collapse whitespace and drop standalone particles
    tokens = [t for t in s.split() if t and t not in ("al", "el")]

    # Map transliteration synonyms
    canonical_tokens = [_TRANSLITERATION_SYNONYMS.get(t, t) for t in tokens]

    return " ".join(canonical_tokens)


def normalize_name(name: str) -> str:
    """Determine script and return canonical normalized string representation."""
    if not name:
        return ""

    # Check for Arabic characters
    if re.search(r"[\u0600-\u06FF]", name):
        return normalize_arabic_text(name)

    return normalize_english_text(name)


def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Compute Jaro-Winkler string similarity between two strings (0.0 to 1.0)."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if not s2_matches[j] and s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    # Transpositions
    transpositions = 0
    k = 0
    for i in range(len1):
        if s1_matches[i]:
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

    transpositions //= 2

    jaro = (
        (matches / len1) + (matches / len2) + ((matches - transpositions) / matches)
    ) / 3.0

    # Winkler prefix scale (up to 4 chars)
    prefix = 0
    max_prefix = min(4, min(len1, len2))
    for i in range(max_prefix):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + (prefix * 0.1 * (1.0 - jaro))


def token_sort_similarity(s1: str, s2: str) -> float:
    """Compute token sort ratio using difflib for word order insensitivity."""
    tokens1 = sorted(s1.split())
    tokens2 = sorted(s2.split())
    sorted_s1 = " ".join(tokens1)
    sorted_s2 = " ".join(tokens2)
    return difflib.SequenceMatcher(None, sorted_s1, sorted_s2).ratio()


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate the best name similarity between two strings using multiple algorithms."""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    if not norm1 or not norm2:
        return 0.0

    if norm1 == norm2:
        return 1.0

    t1 = norm1.split()
    t2 = norm2.split()
    first_name_match = (t1[0] == t2[0]) if (t1 and t2) else False

    # Substring containment check - valid if first names align or one is a direct string prefix
    if norm1 in norm2 or norm2 in norm1:
        if first_name_match or norm1.startswith(norm2) or norm2.startswith(norm1):
            len_ratio = min(len(norm1), len(norm2)) / max(len(norm1), len(norm2))
            if len_ratio > 0.6:
                return 0.90 + (0.10 * len_ratio)

    # Token subset match with matching first name (e.g. missing middle name)
    if t1 and t2 and first_name_match:
        s1, s2 = set(t1), set(t2)
        if s1.issubset(s2) or s2.issubset(s1):
            ratio = min(len(s1), len(s2)) / max(len(s1), len(s2))
            if ratio >= 0.5:
                return max(0.88, 0.82 + (0.15 * ratio))

    jw = jaro_winkler_similarity(norm1, norm2)
    ts = token_sort_similarity(norm1, norm2)
    seq = difflib.SequenceMatcher(None, norm1, norm2).ratio()

    return max(jw, ts, seq)


class EntityResolutionService:
    """Multi-signal entity resolution and explainable matching service."""

    def __init__(
        self,
        name_weight: float = 0.50,
        dob_weight: float = 0.25,
        country_weight: float = 0.15,
        id_weight: float = 0.10,
        potential_match_threshold: float = 0.70,
    ) -> None:
        self.w_name = name_weight
        self.w_dob = dob_weight
        self.w_country = country_weight
        self.w_id = id_weight
        self.threshold = potential_match_threshold

    def score_candidate(
        self,
        query_entity: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        """Score candidate entity against query entity using multi-signal scoring.

        Args:
            query_entity: Dict with keys 'name', optional 'birth_date', 'countries', 'identification_number', 'entity_type'
            candidate: OpenSanctions FollowTheMoney entity dict.

        Returns:
            Dict containing confidence_score, name_similarity, matched_fields,
            conflicting_fields, missing_fields, reasoning, and review_required.
        """
        q_name = query_entity.get("name", "").strip()
        q_dob = query_entity.get("birth_date", "").strip() if query_entity.get("birth_date") else None
        q_countries = [c.lower().strip() for c in query_entity.get("countries", []) if c]
        q_id = query_entity.get("identification_number", "").strip() if query_entity.get("identification_number") else None

        props = candidate.get("properties", {})
        cand_names = [candidate.get("caption", "")] + props.get("name", []) + props.get("alias", [])
        cand_names = [n for n in cand_names if n]

        cand_dobs = props.get("birthDate", [])
        cand_countries = [
            c.lower().strip()
            for c in (
                props.get("country", [])
                + props.get("nationality", [])
                + props.get("citizenship", [])
                + props.get("jurisdiction", [])
            )
            if c
        ]
        cand_ids = props.get("idNumber", []) + props.get("taxNumber", []) + props.get("passportNumber", [])

        matched_fields: list[str] = []
        conflicting_fields: list[str] = []
        missing_fields: list[str] = []

        # 1. Name Signal
        best_name_sim = 0.0
        best_matched_cand_name = ""
        for cn in cand_names:
            sim = calculate_name_similarity(q_name, cn)
            if sim > best_name_sim:
                best_name_sim = sim
                best_matched_cand_name = cn

        if best_name_sim >= 0.75:
            matched_fields.append(
                f"Name match: '{q_name}' ~ '{best_matched_cand_name}' (similarity: {best_name_sim:.2f})"
            )
        elif best_name_sim >= 0.60:
            matched_fields.append(
                f"Partial name similarity: '{q_name}' ~ '{best_matched_cand_name}' (similarity: {best_name_sim:.2f})"
            )
        else:
            conflicting_fields.append(
                f"Low name similarity: '{q_name}' vs candidate '{candidate.get('caption')}' (score: {best_name_sim:.2f})"
            )

        # 2. Date of Birth Signal
        dob_score = 0.0
        if q_dob and cand_dobs:
            q_year = q_dob[:4]
            exact_dob_match = any(q_dob == cd for cd in cand_dobs)
            year_match = any(q_year == cd[:4] for cd in cand_dobs)

            if exact_dob_match:
                dob_score = 1.0
                matched_fields.append(f"Date of birth exact match: {q_dob}")
            elif year_match:
                dob_score = 0.6
                matched_fields.append(f"Birth year match: {q_year} (candidate dates: {', '.join(cand_dobs)})")
            else:
                # Year mismatch penalty
                dob_score = -0.35
                conflicting_fields.append(
                    f"Date of birth mismatch: query '{q_dob}' vs candidate '{', '.join(cand_dobs)}'"
                )
        elif not q_dob:
            missing_fields.append("Date of birth missing in screening query")
        else:
            missing_fields.append("Date of birth not recorded in candidate watchlist record")

        # 3. Country / Nationality Signal
        country_score = 0.0
        if q_countries and cand_countries:
            common_countries = set(q_countries).intersection(set(cand_countries))
            if common_countries:
                country_score = 1.0
                matched_fields.append(f"Country match: {', '.join(c.upper() for c in common_countries)}")
            else:
                country_score = -0.20
                conflicting_fields.append(
                    f"Country conflict: query '{', '.join(c.upper() for c in q_countries)}' vs candidate '{', '.join(c.upper() for c in cand_countries)}'"
                )
        elif not q_countries:
            missing_fields.append("Country/nationality not provided in query")
        else:
            missing_fields.append("Country/nationality not recorded on watchlist record")

        # 4. Identification Number Signal
        id_score = 0.0
        if q_id and cand_ids:
            clean_qid = re.sub(r"[\s\-]", "", q_id.lower())
            clean_cids = [re.sub(r"[\s\-]", "", str(cid).lower()) for cid in cand_ids]
            if clean_qid in clean_cids:
                id_score = 1.0
                matched_fields.append(f"Identification number exact match: {q_id}")
            else:
                id_score = -0.30
                conflicting_fields.append(f"Identification mismatch: '{q_id}' vs '{', '.join(cand_ids)}'")
        elif not q_id:
            missing_fields.append("Identification number not provided in query")
        else:
            missing_fields.append("Identification number not present on watchlist record")

        # Calculate composite score with dynamic weight re-normalization over available attributes
        available_weights = self.w_name
        if q_dob and cand_dobs:
            available_weights += self.w_dob
        if q_countries and cand_countries:
            available_weights += self.w_country
        if q_id and cand_ids:
            available_weights += self.w_id

        # Positive corroboration normalized over available evidence
        composite = (self.w_name / available_weights) * best_name_sim
        if q_dob and cand_dobs and dob_score > 0:
            composite += (self.w_dob / available_weights) * dob_score
        if q_countries and cand_countries and country_score > 0:
            composite += (self.w_country / available_weights) * country_score
        if q_id and cand_ids and id_score > 0:
            composite += (self.w_id / available_weights) * id_score

        # Subtract explicit conflict penalties directly from composite
        if dob_score < 0:
            composite += dob_score  # negative penalty
        if country_score < 0:
            composite += country_score  # negative penalty
        if id_score < 0:
            composite += id_score  # negative penalty

        # Priority boost for confirmed sanctions watchlist designations vs general political PEPs
        cand_topics = props.get("topics", [])
        cand_sanctions = props.get("sanctions", [])
        if ("sanction" in cand_topics or bool(cand_sanctions)) and composite >= self.threshold:
            composite += 0.05

        # Bound composite score to [0.0, 1.0]
        final_confidence = max(0.0, min(1.0, round(composite, 3)))

        # Build explainable narrative reasoning
        candidate_caption = candidate.get("caption", "Unknown Entity")
        sanctions_programs = props.get("sanctions", []) or props.get("topics", [])
        prog_str = f" on programs: {', '.join(sanctions_programs[:2])}" if sanctions_programs else ""

        if final_confidence >= 0.85:
            reasoning = (
                f"HIGH CONFIDENCE MATCH ({final_confidence:.1%}): Entity '{q_name}' strongly aligns with "
                f"sanctioned record '{candidate_caption}'{prog_str}. "
                f"Corroborated by {len(matched_fields)} matching factors. Immediate compliance review required."
            )
            recommendation = "POTENTIAL_MATCH"
            review_required = True
        elif final_confidence >= self.threshold:
            reasoning = (
                f"MODERATE MATCH / REVIEW NEEDED ({final_confidence:.1%}): Entity '{q_name}' has significant "
                f"name similarity with '{candidate_caption}'{prog_str}. "
                f"{len(conflicting_fields)} conflicting attribute(s) or missing secondary identifiers require manual clearance."
            )
            recommendation = "NEEDS_HUMAN_REVIEW"
            review_required = True
        else:
            reasoning = (
                f"LOW CONFIDENCE / LIKELY FALSE POSITIVE ({final_confidence:.1%}): Candidate '{candidate_caption}' "
                f"fails key identity corroboration or exhibits material attribute conflicts."
            )
            recommendation = "NO_MATCH"
            review_required = False

        return {
            "entity_id": candidate.get("id"),
            "caption": candidate_caption,
            "entity_type": candidate.get("schema"),
            "confidence_score": final_confidence,
            "name_similarity": round(best_name_sim, 3),
            "recommendation": recommendation,
            "review_required": review_required,
            "matched_fields": matched_fields,
            "conflicting_fields": conflicting_fields,
            "missing_fields": missing_fields,
            "reasoning": reasoning,
            "sanctions_details": {
                "datasets": candidate.get("datasets", []),
                "sanctions_programs": props.get("sanctions", []),
                "topics": props.get("topics", []),
                "notes": props.get("notes", []),
            },
            "source_citations": candidate.get("source_urls", []),
        }

    def resolve_and_rank(
        self,
        query_entity: dict[str, Any],
        candidates: list[dict[str, Any]],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Score and rank all candidates for a given query entity."""
        scored = [self.score_candidate(query_entity, cand) for cand in candidates]
        # Sort descending by confidence score
        scored.sort(key=lambda x: x["confidence_score"], reverse=True)
        return scored[:limit]
