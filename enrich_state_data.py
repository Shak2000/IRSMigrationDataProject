"""
enrich_state_data.py — Milestone 1.2

General-purpose script that enriches any IRS state inflow or outflow CSV by
joining the y2_statefips column against state_fips.csv and appending two new
columns:

    y2_state_postal  — two-letter postal abbreviation for the y2 state
    y2_state_name    — full name of the y2 state

Special y2_statefips codes that have no entry in state_fips.csv receive
canonical descriptive labels:

    96  →  postal="US+FO",  name="Total Migration-US and Foreign"
    97  →  postal="US",     name="Total Migration-US"
    98  →  postal="FO",     name="Total Migration-Foreign"

Usage
-----
    # Enrich a single file:
    python enrich_state_data.py <input_csv> <output_csv>

    # Batch-produce all four enriched files (no arguments):
    python enrich_state_data.py
"""

import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
STATE_FIPS_CSV = Path("state_fips.csv")

# Raw → enriched file pairs for batch mode
BATCH_FILES: list[tuple[str, str]] = [
    ("stateinflow2122.csv",  "stateinflow2122_enriched.csv"),
    ("stateinflow2223.csv",  "stateinflow2223_enriched.csv"),
    ("stateoutflow2122.csv", "stateoutflow2122_enriched.csv"),
    ("stateoutflow2223.csv", "stateoutflow2223_enriched.csv"),
]

# ---------------------------------------------------------------------------
# Special FIPS code labels (not present in state_fips.csv)
# ---------------------------------------------------------------------------
SPECIAL_FIPS: dict[str, tuple[str, str]] = {
    "96": ("US+FO", "Total Migration-US and Foreign"),
    "97": ("US",    "Total Migration-US"),
    "98": ("FO",    "Total Migration-Foreign"),
}


def load_state_fips(path: Path = STATE_FIPS_CSV) -> dict[str, tuple[str, str]]:
    """
    Load state_fips.csv into a dict keyed by zero-padded 2-digit FIPS code.

    Returns
    -------
    dict[fips_code -> (state_postal, state_name)]
    """
    lookup: dict[str, tuple[str, str]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fips = row["fips_code"].strip().zfill(2)
            lookup[fips] = (row["state_postal"].strip(), row["state_name"].strip())
    # Merge in special codes
    lookup.update({k: v for k, v in SPECIAL_FIPS.items()})
    return lookup


def enrich(input_path: str | Path, output_path: str | Path,
           fips_lookup: dict[str, tuple[str, str]]) -> int:
    """
    Read *input_path*, append y2_state_postal and y2_state_name columns,
    and write to *output_path*.

    Returns the number of data rows written (excluding the header).

    Raises
    ------
    KeyError
        If a y2_statefips value is not found in fips_lookup.  The offending
        code is included in the error message.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    rows_written = 0
    missing_codes: set[str] = set()

    with (
        open(input_path, newline="", encoding="utf-8") as fh_in,
        open(output_path, "w", newline="", encoding="utf-8") as fh_out,
    ):
        reader = csv.DictReader(fh_in)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or header-less file: {input_path}")

        # Build output field list: all original columns + two new ones at end
        out_fields = list(reader.fieldnames) + ["y2_state", "y2_state_name"]
        writer = csv.DictWriter(fh_out, fieldnames=out_fields)
        writer.writeheader()

        for row in reader:
            raw_fips = row["y2_statefips"].strip()
            padded = raw_fips.zfill(2)

            if padded in fips_lookup:
                postal, name = fips_lookup[padded]
            else:
                missing_codes.add(raw_fips)
                postal, name = "", ""

            row["y2_state"] = postal
            row["y2_state_name"] = name
            writer.writerow(row)
            rows_written += 1

    if missing_codes:
        print(
            f"  WARNING: {len(missing_codes)} unrecognised y2_statefips value(s) in "
            f"{input_path.name}: {sorted(missing_codes)}"
        )

    return rows_written


def main() -> None:
    # ── Single-file mode ─────────────────────────────────────────────────────
    if len(sys.argv) == 3:
        input_csv = sys.argv[1]
        output_csv = sys.argv[2]

        if not STATE_FIPS_CSV.exists():
            sys.exit(f"ERROR: {STATE_FIPS_CSV} not found. Run parse_fips.py first.")

        print(f"Loading {STATE_FIPS_CSV} …")
        fips_lookup = load_state_fips()

        print(f"Enriching {input_csv} → {output_csv} …")
        n = enrich(input_csv, output_csv, fips_lookup)
        print(f"  Wrote {n:,} rows → {output_csv}")

    # ── Batch mode (no arguments) ─────────────────────────────────────────────
    elif len(sys.argv) == 1:
        if not STATE_FIPS_CSV.exists():
            sys.exit(f"ERROR: {STATE_FIPS_CSV} not found. Run parse_fips.py first.")

        print(f"Loading {STATE_FIPS_CSV} …")
        fips_lookup = load_state_fips()
        print(f"  {len(fips_lookup)} FIPS entries loaded (including special codes)\n")

        for input_csv, output_csv in BATCH_FILES:
            if not Path(input_csv).exists():
                print(f"  SKIP: {input_csv} not found")
                continue
            print(f"Enriching {input_csv} → {output_csv} …")
            n = enrich(input_csv, output_csv, fips_lookup)
            print(f"  Wrote {n:,} rows ✓")

        print("\nDone.")

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
