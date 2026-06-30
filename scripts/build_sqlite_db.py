"""
scripts/build_sqlite_db.py — Milestone 10.2

Consolidates all enriched CSV files into a single optimized SQLite database.
This removes the need for the browser to download and parse massive CSVs into memory.

Usage
-----
    python scripts/build_sqlite_db.py
"""

import sqlite3
import csv
import sys
import re
from pathlib import Path

DB_PATH = Path("data/database.sqlite")
ENRICHED_DIR = Path("data/enriched")

STATE_FLOWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS state_flows (
    year TEXT,
    direction TEXT,
    y2_state TEXT,
    y2_state_name TEXT,
    y2_statefips TEXT,
    y1_statefips TEXT,
    y1_state TEXT,
    y1_state_name TEXT,
    n1 INTEGER,
    n2 INTEGER,
    AGI INTEGER
);
"""

COUNTY_FLOWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS county_flows (
    year TEXT,
    direction TEXT,
    y2_state TEXT,
    y2_state_name TEXT,
    y2_statefips TEXT,
    y2_countyfips TEXT,
    y2_county_name TEXT,
    y1_statefips TEXT,
    y1_countyfips TEXT,
    y1_state TEXT,
    y1_state_name TEXT,
    y1_county_name TEXT,
    n1 INTEGER,
    n2 INTEGER,
    AGI INTEGER
);
"""

def extract_metadata(filename: str) -> tuple[str, str, str]:
    """Extracts (level, direction, year) from a filename.
    E.g., stateinflow2122_enriched.csv -> ('state', 'inflow', '2122')
    """
    match = re.match(r"(state|county)(inflow|outflow)(\d{4})_enriched\.csv", filename)
    if not match:
        raise ValueError(f"Could not parse filename: {filename}")
    return match.groups()

def parse_int(val: str) -> int:
    try:
        return int(float(val)) if val.strip() else 0
    except ValueError:
        return 0

def insert_file(cursor: sqlite3.Cursor, filepath: Path, level: str, direction: str, year: str) -> int:
    table_name = f"{level}_flows"
    rows_inserted = 0
    
    with open(filepath, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        
        if level == "state":
            sql = f"""
                INSERT INTO {table_name} 
                (year, direction, y2_state, y2_state_name, y2_statefips, y1_statefips, y1_state, y1_state_name, n1, n2, AGI)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            batch = []
            for row in reader:
                batch.append((
                    year, direction,
                    row["y2_state"], row["y2_state_name"], row["y2_statefips"],
                    row["y1_statefips"], row["y1_state"], row["y1_state_name"],
                    parse_int(row["n1"]), parse_int(row["n2"]), parse_int(row["AGI"])
                ))
            cursor.executemany(sql, batch)
            rows_inserted = len(batch)
            
        elif level == "county":
            sql = f"""
                INSERT INTO {table_name}
                (year, direction, y2_state, y2_state_name, y2_statefips, y2_countyfips, y2_county_name, y1_statefips, y1_countyfips, y1_state, y1_state_name, y1_county_name, n1, n2, AGI)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            batch = []
            for row in reader:
                batch.append((
                    year, direction,
                    row["y2_state"], row["y2_state_name"], row["y2_statefips"], row["y2_countyfips"], row["y2_county_name"],
                    row["y1_statefips"], row["y1_countyfips"], row["y1_state"], row["y1_state_name"], row["y1_county_name"],
                    parse_int(row["n1"]), parse_int(row["n2"]), parse_int(row["AGI"])
                ))
            cursor.executemany(sql, batch)
            rows_inserted = len(batch)

    return rows_inserted

def main():
    print(f"Building SQLite database at {DB_PATH}...\n")
    
    if DB_PATH.exists():
        print(f"Removing existing database at {DB_PATH}")
        DB_PATH.unlink()
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create schema
    cursor.execute(STATE_FLOWS_SCHEMA)
    cursor.execute(COUNTY_FLOWS_SCHEMA)
    
    total_files = 0
    total_rows = 0
    
    # Iterate over all CSVs in data/enriched/
    for folder in ENRICHED_DIR.iterdir():
        if folder.is_dir():
            for filepath in folder.glob("*.csv"):
                try:
                    level, direction, year = extract_metadata(filepath.name)
                except ValueError as e:
                    print(f"  [SKIP] {e}")
                    continue
                    
                print(f"  Processing {filepath.name}...")
                n = insert_file(cursor, filepath, level, direction, year)
                total_files += 1
                total_rows += n
    
    print("\nCreating indexes...")
    # Add indexes for fast querying by the frontend
    cursor.execute("CREATE INDEX idx_state_year_dir ON state_flows(year, direction)")
    cursor.execute("CREATE INDEX idx_state_y2 ON state_flows(y2_statefips)")
    cursor.execute("CREATE INDEX idx_state_y1 ON state_flows(y1_statefips)")
    
    cursor.execute("CREATE INDEX idx_county_year_dir ON county_flows(year, direction)")
    cursor.execute("CREATE INDEX idx_county_y2 ON county_flows(y2_statefips, y2_countyfips)")
    cursor.execute("CREATE INDEX idx_county_y1 ON county_flows(y1_statefips, y1_countyfips)")
    
    conn.commit()
    
    # Vacuum to compress and optimize the database
    print("Optimizing database (VACUUM)...")
    cursor.execute("VACUUM")
    
    conn.close()
    
    # Get final file size
    size_mb = DB_PATH.stat().st_size / (1024 * 1024)
    print(f"\nDone. Inserted {total_rows:,} rows from {total_files} files.")
    print(f"Database size: {size_mb:.1f} MB")

if __name__ == "__main__":
    main()
