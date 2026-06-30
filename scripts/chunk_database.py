"""
scripts/chunk_database.py

Splits the database.sqlite into 10MB chunks and generates the config for sql.js-httpvfs.
"""
import os
import math
import json
from pathlib import Path

DB_PATH = Path("data/database.sqlite")
OUT_DIR = Path("data/db_chunks")
CHUNK_SIZE = 40 * 1024 * 1024 # 40MB

def main():
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found.")
        return
        
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # clear existing chunks
    for f in OUT_DIR.glob("database.sqlite.*"):
        f.unlink()
        
    file_size = DB_PATH.stat().st_size
    num_chunks = math.ceil(file_size / CHUNK_SIZE)
    print(f"Total size: {file_size} bytes. Splitting into {num_chunks} chunks...")
    
    with open(DB_PATH, 'rb') as f_in:
        for i in range(num_chunks):
            chunk_data = f_in.read(CHUNK_SIZE)
            # Use 3 digit zero padded index like 000, 001
            chunk_filename = f"database.sqlite.{i:03d}"
            out_path = OUT_DIR / chunk_filename
            with open(out_path, 'wb') as f_out:
                f_out.write(chunk_data)
            print(f"  Written {out_path} ({len(chunk_data)} bytes)")
            
    # Generate the config JSON block needed by sql.js-httpvfs
    config = {
        "serverMode": "chunked",
        "requestChunkSize": 4096,
        "databaseLengthBytes": file_size,
        "serverChunkSize": CHUNK_SIZE,
        "urlPrefix": "data/db_chunks/database.sqlite.",
        "suffixLength": 3
    }
    
    config_path = OUT_DIR / "config.json"
    with open(config_path, 'w') as f_out:
        json.dump(config, f_out, indent=2)
        
    print(f"\nDone! Config written to {config_path}")
    print(json.dumps(config, indent=2))

if __name__ == "__main__":
    main()
