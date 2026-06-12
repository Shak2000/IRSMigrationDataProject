"""
parse_fips.py — Milestone 1.1

Reads fips.txt and produces two CSV files:
  state_fips.csv   — columns: fips_code, state_name, state_postal
  county_fips.csv  — columns: state_fips, county_fips, county_name, state_name, state_postal

The input file has two fixed-width sections:
  1. State-level block  — FIPS codes are 2-digit (right-justified in ~8-char field)
  2. County-level block — FIPS codes are 5-digit (right-justified in ~6-char field)
     Within the county block, rows whose last 3 digits are "000" are state-summary rows
     (e.g., "01000  Alabama") and are used only to associate subsequent county rows with
     a state; they are NOT written to county_fips.csv as counties.

County names in the source file sometimes contain trailing parenthetical notes
(e.g., "Denali Borough                         (created after 1990)"). These are
stripped so that only the clean place name is stored.
"""

import csv
import re

# ---------------------------------------------------------------------------
# State name → two-letter postal abbreviation
# ---------------------------------------------------------------------------
STATE_POSTAL = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
}

# Pattern for a data row: optional whitespace, digits, whitespace, place name
DATA_ROW = re.compile(r"^\s+(\d+)\s{2,}(.+?)\s*$")


def clean_place_name(name: str) -> str:
    """Remove trailing parenthetical annotations and excess whitespace from a place name.

    Examples
    --------
    "Denali Borough                         (created after 1990)" → "Denali Borough"
    "Autauga County" → "Autauga County"
    """
    # Strip everything from the first '(' onward, then strip surrounding whitespace
    paren_idx = name.find("(")
    if paren_idx != -1:
        name = name[:paren_idx]
    return name.strip()


def parse_fips(input_path: str = "fips.txt") -> tuple[list[dict], list[dict]]:
    """
    Parse fips.txt into two lists of records.

    Returns
    -------
    state_rows  : list of dict with keys fips_code, state_name, state_postal
    county_rows : list of dict with keys state_fips, county_fips,
                  county_name, state_name, state_postal
    """
    state_rows: list[dict] = []
    county_rows: list[dict] = []

    # Track which section we are in and the current state context
    in_county_section = False
    current_state_fips: str | None = None
    current_state_name: str | None = None
    current_state_postal: str | None = None

    with open(input_path, encoding="utf-8") as fh:
        for line in fh:
            # Detect section header for county block
            if "county-level" in line.lower():
                in_county_section = True
                continue

            match = DATA_ROW.match(line)
            if not match:
                continue

            code_str = match.group(1).strip()
            name = match.group(2).strip()

            if not in_county_section:
                # ── State section ──────────────────────────────────────────
                # Codes here are 2-digit state FIPS
                fips_code = code_str.zfill(2)
                upper_name = name.upper()
                postal = STATE_POSTAL.get(upper_name, "")
                state_rows.append(
                    {
                        "fips_code": fips_code,
                        "state_name": name.title() if upper_name not in ("DISTRICT OF COLUMBIA",) else name.title(),
                        "state_postal": postal,
                    }
                )
            else:
                # ── County section ─────────────────────────────────────────
                # Codes here are 5-digit: SSCCC  (SS = state, CCC = county)
                full_code = code_str.zfill(5)
                state_fips = full_code[:2]
                county_fips = full_code[2:]

                if county_fips == "000":
                    # State-summary row — update context, do not emit a county
                    current_state_fips = state_fips
                    current_state_name_raw = name.upper()
                    current_state_name = clean_place_name(name)  # preserve original casing
                    current_state_postal = STATE_POSTAL.get(current_state_name_raw, "")
                else:
                    # Real county row
                    county_rows.append(
                        {  # noqa: E501
                            "state_fips": state_fips,
                            "county_fips": county_fips,
                            "county_name": clean_place_name(name),
                            "state_name": current_state_name,
                            "state_postal": current_state_postal,
                        }
                    )

    return state_rows, county_rows


def write_csv(path: str, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows):,} rows → {path}")


def main() -> None:
    print("Parsing fips.txt …")
    state_rows, county_rows = parse_fips("fips.txt")

    print(f"  Found {len(state_rows)} state entries")
    print(f"  Found {len(county_rows):,} county entries")

    write_csv(
        "state_fips.csv",
        fieldnames=["fips_code", "state_name", "state_postal"],
        rows=state_rows,
    )
    write_csv(
        "county_fips.csv",
        fieldnames=["state_fips", "county_fips", "county_name", "state_name", "state_postal"],
        rows=county_rows,
    )

    # Quick sanity checks
    missing_postal = [r for r in state_rows if not r["state_postal"]]
    if missing_postal:
        print(f"\n  WARNING: {len(missing_postal)} state(s) have no postal code:")
        for r in missing_postal:
            print(f"    {r}")
    else:
        print("\n  ✓ All states have postal codes")

    missing_county_postal = [r for r in county_rows if not r["state_postal"]]
    if missing_county_postal:
        print(f"  WARNING: {len(missing_county_postal)} county rows have no state postal code")
    else:
        print("  ✓ All county rows have state postal codes")


if __name__ == "__main__":
    main()
