#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import gzip
import heapq
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RankedCid:
    synonym_count: int
    cid: int

    @property
    def heap_key(self) -> tuple[int, int]:
        # Higher synonym count wins; for ties, the smaller CID wins.
        return (self.synonym_count, -self.cid)


def iter_gzip_tsv(path: Path):
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        for raw_line in handle:
            yield raw_line.rstrip("\n").split("\t")


def finish_cid(
    heap: list[tuple[tuple[int, int], RankedCid]],
    cid: int | None,
    unique_synonyms: set[str],
    limit: int,
) -> None:
    if cid is None:
        return
    ranked = RankedCid(synonym_count=len(unique_synonyms), cid=cid)
    entry = (ranked.heap_key, ranked)
    if len(heap) < limit:
        heapq.heappush(heap, entry)
        return
    if entry[0] > heap[0][0]:
        heapq.heapreplace(heap, entry)


def select_top_cids(synonym_path: Path, limit: int) -> dict[int, int]:
    heap: list[tuple[tuple[int, int], RankedCid]] = []
    current_cid: int | None = None
    unique_synonyms: set[str] = set()

    for parts in iter_gzip_tsv(synonym_path):
        cid = int(parts[0])
        synonym = parts[1]
        if current_cid is None:
            current_cid = cid
        if cid != current_cid:
            finish_cid(heap, current_cid, unique_synonyms, limit)
            current_cid = cid
            unique_synonyms = set()
        unique_synonyms.add(synonym)

    finish_cid(heap, current_cid, unique_synonyms, limit)

    ranked = [item for _, item in heap]
    ranked.sort(key=lambda item: (-item.synonym_count, item.cid))
    return {item.cid: item.synonym_count for item in ranked}


def collect_synonyms(synonym_path: Path, selected_cids: set[int]) -> dict[int, list[str]]:
    synonyms_by_cid: dict[int, list[str]] = {}
    seen_by_cid: dict[int, set[str]] = {}

    for parts in iter_gzip_tsv(synonym_path):
        cid = int(parts[0])
        if cid not in selected_cids:
            continue
        synonym = parts[1]
        seen = seen_by_cid.setdefault(cid, set())
        if synonym in seen:
            continue
        seen.add(synonym)
        synonyms_by_cid.setdefault(cid, []).append(synonym)

    return synonyms_by_cid


def collect_single_value(path: Path, selected_cids: set[int]) -> dict[int, str]:
    values: dict[int, str] = {}
    remaining = set(selected_cids)
    for parts in iter_gzip_tsv(path):
        cid = int(parts[0])
        if cid not in remaining:
            continue
        values[cid] = parts[1]
        remaining.remove(cid)
        if not remaining:
            break
    return values


def write_dataset(
    output_path: Path,
    ranked_counts: dict[int, int],
    synonyms_by_cid: dict[int, list[str]],
    smiles_by_cid: dict[int, str],
    iupac_by_cid: dict[int, str],
) -> None:
    ordered_cids = sorted(ranked_counts, key=lambda cid: (-ranked_counts[cid], cid))
    with gzip.open(output_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["cid", "synonym_count", "smiles", "iupac", "synonyms_json"])
        for cid in ordered_cids:
            writer.writerow(
                [
                    cid,
                    ranked_counts[cid],
                    smiles_by_cid.get(cid, ""),
                    iupac_by_cid.get(cid, ""),
                    json.dumps(synonyms_by_cid.get(cid, []), ensure_ascii=False),
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a gzipped TSV with the top PubChem molecules by synonym count."
    )
    parser.add_argument(
        "--pubchem-dir",
        type=Path,
        default=Path("/home/ra/Datasets/PubChem"),
        help="Directory with CID-Synonym-filtered.gz, CID-SMILES.gz, and CID-IUPAC.gz",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("top-10k.tsv.gz"),
        help="Output gzipped TSV path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10_000,
        help="Number of top molecules to keep",
    )
    args = parser.parse_args()

    synonym_path = args.pubchem_dir / "CID-Synonym-filtered.gz"
    smiles_path = args.pubchem_dir / "CID-SMILES.gz"
    iupac_path = args.pubchem_dir / "CID-IUPAC.gz"

    ranked_counts = select_top_cids(synonym_path, args.limit)
    selected_cids = set(ranked_counts)
    synonyms_by_cid = collect_synonyms(synonym_path, selected_cids)
    smiles_by_cid = collect_single_value(smiles_path, selected_cids)
    iupac_by_cid = collect_single_value(iupac_path, selected_cids)
    write_dataset(args.output, ranked_counts, synonyms_by_cid, smiles_by_cid, iupac_by_cid)


if __name__ == "__main__":
    main()
