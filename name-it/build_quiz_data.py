#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import difflib
import gzip
import json
import random
import re
import sys
from pathlib import Path


DEFAULT_OPTION_COUNT = 6
DEFAULT_CORRECT_COUNT = 2
DEFAULT_SEED = 20260326
MAX_CORRECT_POOL = 12
MAX_DECOY_POOL = 4
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
TRAILING_PAREN_RE = re.compile(r"^(?P<base>.*?)(?P<gap>\s*)\((?P<content>[^()]*)\)\s*$")
TRAILING_BRACKET_RE = re.compile(r"^(?P<base>.*?)\s*\[(?P<content>[^\[\]]*)\]\s*$")
IDENTIFIER_PREFIXES = (
    "CCRIS",
    "CHEBI",
    "DTXSID",
    "MFCD",
    "NSC",
    "SCHEMBL",
    "UNII",
)
NOISE_KEYWORDS = (
    "ACGIH",
    "ANSI",
    "BAN",
    "BEILSTEIN",
    "BOOK",
    "BSI",
    "CERTIFIED REFERENCE MATERIAL",
    "CORROSIVE",
    "DCIT",
    "DOT",
    "DSC",
    "EMA EPAR",
    "FCC",
    "FHFI",
    "FLAMMABLE",
    "GC",
    "GMP",
    "GREEN BOOK",
    "HSDB",
    "HPLC",
    "HPUS",
    "IARC",
    "INCI",
    "INN",
    "JAN",
    "JP",
    "LANGUAL",
    "MART",
    "METALS BASIS",
    "MI",
    "MONOGRAPH",
    "NF",
    "ORANGE BOOK",
    "OSHA",
    "POISON",
    "PREMION",
    "PURATRONIC",
    "REAGENTPLUS",
    "STANDARD",
    "STREET NAME",
    "TLC",
    "TN",
    "TRACECERT",
    "UN ",
    "USAN",
    "USP",
    "VAN",
    "VANDF",
    "VETERINARY",
    "WHO-",
    "WHO ",
)
NOISE_EXACT = {
    "0",
    "1:1",
    "1:2",
    "2:1",
    "8CI",
    "9CI",
    "II",
    "R",
    "S",
    "T",
}
CHEMICAL_HINTS = (
    "acid",
    "adenosine",
    "alcohol",
    "amide",
    "amine",
    "amino",
    "benzo",
    "brom",
    "calcium",
    "chlor",
    "copper",
    "ethyl",
    "fluor",
    "glutamic",
    "hydroxy",
    "iron",
    "lidocaine",
    "magnesium",
    "meth",
    "methyl",
    "nickel",
    "oxide",
    "phosphate",
    "potassium",
    "propyl",
    "purine",
    "ribofuranosyl",
    "riboside",
    "salicy",
    "silver",
    "sodium",
    "sulf",
    "tetrahydrofuran",
    "titan",
    "zinc",
)


def normalize_name(value: str) -> str:
    return " ".join(value.split())


def normalize_key(value: str) -> str:
    return normalize_name(value).casefold()


def looks_like_noise_annotation(content: str) -> bool:
    normalized = normalize_name(content).strip(" ,;:/")
    if not normalized:
        return True

    upper = normalized.upper()

    if upper in NOISE_EXACT:
        return True
    if any(keyword in upper for keyword in NOISE_KEYWORDS):
        return True
    if re.fullmatch(r"[A-Z0-9:+./ -]{1,36}", upper) and any(character.isdigit() for character in upper):
        return True
    if normalized.lower() in {
        "czech",
        "dutch",
        "french",
        "german",
        "italian",
        "latin",
        "polish",
        "spanish",
    }:
        return True

    return False


def strip_trailing_annotations(name: str) -> str:
    cleaned = normalize_name(name)

    while cleaned:
        paren_match = TRAILING_PAREN_RE.match(cleaned)
        if paren_match:
            content = paren_match.group("content")
            if looks_like_noise_annotation(content) or not paren_match.group("gap"):
                cleaned = paren_match.group("base").rstrip(" ,;/")
                continue

        bracket_match = TRAILING_BRACKET_RE.match(cleaned)
        if bracket_match and looks_like_noise_annotation(bracket_match.group("content")):
            cleaned = bracket_match.group("base").rstrip(" ,;/")
            continue

        break

    return cleaned


def looks_like_chemical_name(name: str) -> bool:
    lower = name.casefold()
    return any(keyword in lower for keyword in CHEMICAL_HINTS)


def is_human_readable_name(name: str) -> bool:
    if CAS_RE.match(name):
        return False

    letters = sum(character.isalpha() for character in name)
    digits = sum(character.isdigit() for character in name)
    compact = name.replace(" ", "").replace("-", "")
    upper_name = name.upper()

    if letters == 0:
        return False
    if compact.upper().startswith(IDENTIFIER_PREFIXES):
        return False
    if upper_name == name and letters <= 3 and digits == 0:
        return False
    if upper_name == name and digits >= letters and digits > 0:
        return False
    if upper_name == name and re.fullmatch(r"[A-Z0-9]+", compact) and digits > 0 and len(compact) >= 5:
        return False

    return True


def name_score(name: str, index: int, primary_key: str) -> int:
    letters = sum(character.isalpha() for character in name)
    digits = sum(character.isdigit() for character in name)
    score = index

    if is_human_readable_name(name):
        score -= 25
    else:
        score += 400

    if normalize_key(name) == primary_key:
        score -= 35
    if looks_like_chemical_name(name):
        score -= 20
    if "(" in name or "[" in name:
        score += 20
    if digits:
        score += digits * 2
    if name.upper() == name and letters:
        score += 10
    if len(name) <= 3:
        score += 30

    return score


def rank_names(names: list[str]) -> list[str]:
    primary_key = normalize_key(names[0]) if names else ""
    ranked = sorted(
        enumerate(names),
        key=lambda item: (name_score(item[1], item[0], primary_key), item[0]),
    )
    return [name for _, name in ranked]


def similarity_tokens(name: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", name.casefold()))


def compact_similarity_key(name: str) -> str:
    return "".join(re.findall(r"[a-z0-9]+", name.casefold()))


def are_names_too_similar(left: str, right: str) -> bool:
    left_key = normalize_key(left)
    right_key = normalize_key(right)
    if left_key == right_key:
        return True

    left_compact = compact_similarity_key(left)
    right_compact = compact_similarity_key(right)

    if min(len(left_compact), len(right_compact)) >= 6:
        if left_compact in right_compact or right_compact in left_compact:
            return True

    left_tokens = similarity_tokens(left)
    right_tokens = similarity_tokens(right)
    if left_tokens and right_tokens:
        overlap_ratio = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
        if overlap_ratio >= 0.75:
            return True

    ratio = difflib.SequenceMatcher(None, left_compact, right_compact).ratio()
    return ratio >= 0.78


def select_distinct_correct_names(candidates: list[str], desired_count: int) -> list[str]:
    selected: list[str] = []
    for candidate in candidates:
        if any(are_names_too_similar(candidate, existing) for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) == desired_count:
            break

    if selected:
        return selected
    return candidates[:1]


def load_molecules(path: Path) -> list[dict[str, object]]:
    csv.field_size_limit(sys.maxsize)
    molecules: list[dict[str, object]] = []

    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            synonyms = json.loads(row["synonyms_json"])
            deduped_synonyms: list[str] = []
            synonym_keys: set[str] = set()

            for raw_name in synonyms:
                name = strip_trailing_annotations(raw_name)
                if not name:
                    continue
                key = normalize_key(name)
                if key in synonym_keys:
                    continue
                synonym_keys.add(key)
                deduped_synonyms.append(name)

            iupac_name = strip_trailing_annotations(row["iupac"])
            if iupac_name:
                iupac_key = normalize_key(iupac_name)
                if iupac_key not in synonym_keys:
                    synonym_keys.add(iupac_key)
                    deduped_synonyms.append(iupac_name)

            smiles = row["smiles"].strip()
            if not smiles or len(deduped_synonyms) < 2:
                continue

            molecules.append(
                {
                    "cid": int(row["cid"]),
                    "smiles": smiles,
                    "preferred_synonyms": rank_names(deduped_synonyms),
                    "synonyms": deduped_synonyms,
                    "synonym_keys": synonym_keys,
                }
            )

    return molecules


def build_rounds(
    molecules: list[dict[str, object]],
    option_count: int,
    correct_count: int,
    seed: int,
) -> dict[str, object]:
    rng = random.Random(seed)
    decoy_pool: list[tuple[int, str]] = []

    for molecule in molecules:
        cid = molecule["cid"]
        synonyms = molecule["preferred_synonyms"][:MAX_CORRECT_POOL]
        for name in synonyms[:MAX_DECOY_POOL]:
            decoy_pool.append((cid, name))

    rounds: list[dict[str, object]] = []

    for molecule in molecules:
        cid = int(molecule["cid"])
        synonyms = list(molecule["preferred_synonyms"])
        synonym_keys = set(molecule["synonym_keys"])
        preferred_correct = synonyms[:MAX_CORRECT_POOL]
        desired_correct = min(correct_count, len(preferred_correct), option_count - 1)
        correct_names = select_distinct_correct_names(preferred_correct, desired_correct)

        options = [
            {
                "id": f"{cid}:correct:{index}",
                "label": name,
                "isCorrect": True,
            }
            for index, name in enumerate(correct_names)
        ]

        used_option_keys = {normalize_key(option["label"]) for option in options}
        required_decoys = option_count - len(options)
        attempts = 0
        max_attempts = max(len(decoy_pool) * 4, 1)

        while len(options) < option_count and attempts < max_attempts:
            attempts += 1
            decoy_cid, decoy_name = decoy_pool[rng.randrange(len(decoy_pool))]
            decoy_key = normalize_key(decoy_name)

            if decoy_cid == cid:
                continue
            if decoy_key in synonym_keys:
                continue
            if decoy_key in used_option_keys:
                continue

            used_option_keys.add(decoy_key)
            options.append(
                {
                    "id": f"{cid}:decoy:{len(options)}",
                    "label": decoy_name,
                    "isCorrect": False,
                }
            )

        if len(options) != option_count:
            raise RuntimeError(f"Could not build a full option set for CID {cid}.")

        rng.shuffle(options)
        rounds.append(
            {
                "cid": cid,
                "smiles": molecule["smiles"],
                "options": options,
            }
        )

    return {
        "seed": seed,
        "optionCount": option_count,
        "roundCount": len(rounds),
        "rounds": rounds,
    }


def write_js_data(output_path: Path, payload: dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    output_path.write_text(f"window.NameItData={serialized};\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build browser-ready quiz data from the top-10k PubChem TSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("top-10k.tsv.gz"),
        help="Input gzipped TSV produced by build_top_10k.py",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/quiz-data.js"),
        help="Output JS data file consumed directly by the static app",
    )
    parser.add_argument(
        "--option-count",
        type=int,
        default=DEFAULT_OPTION_COUNT,
        help="Number of names shown per round",
    )
    parser.add_argument(
        "--correct-count",
        type=int,
        default=DEFAULT_CORRECT_COUNT,
        help="Number of correct names included per round",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Deterministic seed for round generation",
    )
    args = parser.parse_args()

    molecules = load_molecules(args.input)
    payload = build_rounds(
        molecules=molecules,
        option_count=args.option_count,
        correct_count=args.correct_count,
        seed=args.seed,
    )
    write_js_data(args.output, payload)


if __name__ == "__main__":
    main()
