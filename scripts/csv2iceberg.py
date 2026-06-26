#!/usr/bin/env python3
"""Convert CSV to Iceberg table format (tabular, not vector).

Generates: Parquet data file + metadata.json + manifest list (Avro).

Usage: python3 csv2iceberg.py --csv <data.csv> --out-dir <iceberg_dir>
"""
import argparse, json, os, sys, time, uuid
from pathlib import Path


def build_schema(col_names):
    """Return Iceberg schema fields JSON.
    Maps CSV column names to Iceberg types:
      *_sk, *_id, *_number, *_seq → long
      *_price, *_cost, *_amt, *_tax, *_paid, *_profit, *discount*, *percentage*, *offset* → double
      everything else → string
    """
    fields = []
    for i, name in enumerate(col_names):
        lower = name.lower()
        if any(lower.endswith(suffix) for suffix in
               ('_sk', '_id', '_number', '_seq', '_year', '_month', '_day',
                '_dow', '_moy', '_dom', '_qoy')):
            typ = "long"
        elif any(kw in lower for kw in
                 ('price', 'cost', 'amt', 'tax', 'paid', 'profit', 'discount',
                  'percentage', 'offset')):
            typ = "double"
        else:
            typ = "string"
        fields.append({"id": i + 1, "name": name, "type": typ, "required": False})
    return fields


def write_parquet(csv_path, out_path):
    """Read CSV and write as Parquet file. Returns (row count, file size)."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        import pyarrow.csv as pcsv
    except ImportError:
        print("ERROR: pyarrow required. pip install pyarrow", file=sys.stderr)
        sys.exit(1)

    table = pcsv.read_csv(csv_path)
    pq.write_table(table, out_path)
    size = os.path.getsize(out_path)
    print(f"  → {out_path}: {table.num_rows} rows, {table.num_columns} cols, {size:,} bytes",
          file=sys.stderr)
    return table.num_rows, size


def write_metadata_json(schema_fields, table_uuid, location, data_dir,
                        manifest_rel, out_path):
    """Write minimal Iceberg v1 metadata.json."""
    metadata = {
        "format-version": 1,
        "table-uuid": table_uuid,
        "location": location,
        "last-updated-ms": int(time.time() * 1000),
        "current-schema-id": 0,
        "default-spec-id": 0,
        "partition-specs": [{"spec-id": 0, "fields": []}],
        "schemas": [{
            "schema-id": 0,
            "type": "struct",
            "fields": schema_fields
        }],
        "snapshots": [{
            "snapshot-id": 1,
            "parent-snapshot-id": None,
            "timestamp-ms": int(time.time() * 1000),
            "manifest-list": manifest_rel,
            "summary": {"operation": "append"}
        }],
        "snapshot-log": [{"snapshot-id": 1, "timestamp-ms": int(time.time() * 1000)}],
        "metadata-log": [],
        "properties": {}
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"  → {out_path}", file=sys.stderr)


def write_manifest_avro(data_files, out_path):
    """Write a minimal Iceberg manifest list in Avro format."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    try:
        import fastavro
        schema = {
            "type": "record",
            "name": "manifest_entry",
            "fields": [
                {"name": "status", "type": "int"},
                {"name": "snapshot_id", "type": "long"},
                {"name": "data_file", "type": {
                    "type": "record", "name": "data_file",
                    "fields": [
                        {"name": "file_path", "type": "string"},
                        {"name": "file_format", "type": "string"},
                        {"name": "partition", "type": {"type": "map", "values": "string"}},
                        {"name": "record_count", "type": "long"},
                        {"name": "file_size_in_bytes", "type": "long"},
                        {"name": "column_sizes", "type": {"type": "map", "values": "long"}},
                        {"name": "value_counts", "type": {"type": "map", "values": "long"}},
                        {"name": "null_value_counts", "type": {"type": "map", "values": "long"}},
                        {"name": "lower_bounds", "type": {"type": "map", "values": "bytes"}},
                        {"name": "upper_bounds", "type": {"type": "map", "values": "bytes"}},
                    ]
                }}
            ]
        }
        entries = []
        for df in data_files:
            entries.append({
                "status": 1,  # ADDED
                "snapshot_id": 1,
                "data_file": {
                    "file_path": df["path"],
                    "file_format": "PARQUET",
                    "partition": {},
                    "record_count": df["rows"],
                    "file_size_in_bytes": df["size"],
                    "column_sizes": {},
                    "value_counts": {},
                    "null_value_counts": {},
                    "lower_bounds": {},
                    "upper_bounds": {},
                }
            })
        with open(out_path, 'wb') as f:
            fastavro.writer(f, schema, entries)
        print(f"  → {out_path} (Avro)", file=sys.stderr)
    except ImportError:
        with open(out_path, 'wb') as f:
            f.write(b'\x00' * 4)
        print(f"  → {out_path} (stub, install fastavro for full)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="CSV → Iceberg table converter")
    parser.add_argument('--csv', required=True, help='CSV file with header')
    parser.add_argument('--out-dir', required=True,
                        help='Output Iceberg directory (e.g., /tmp/test_iceberg/tpcds_ss)')
    parser.add_argument('--rows', type=int, default=100,
                        help='Number of rows to include in initial Parquet file (default 100)')
    args = parser.parse_args()

    iceberg_dir = Path(args.out_dir)
    os.makedirs(iceberg_dir, exist_ok=True)

    # Read column names from CSV header
    with open(args.csv) as f:
        header = f.readline().strip()
    col_names = [c.strip() for c in header.split(',')]

    # Build Iceberg schema from column names
    schema_fields = build_schema(col_names)
    print(f"  Schema: {len(schema_fields)} fields", file=sys.stderr)

    # Create a small subset CSV for the initial Parquet snapshot
    subset_csv = iceberg_dir / '_seed.csv'
    with open(subset_csv, 'w') as out:
        out.write(header + '\n')
        with open(args.csv) as fin:
            fin.readline()  # skip header
            for i, line in enumerate(fin):
                if i >= args.rows:
                    break
                out.write(line)

    # Write initial Parquet data file
    data_dir = iceberg_dir / 'data'
    os.makedirs(data_dir, exist_ok=True)
    rows, size = write_parquet(str(subset_csv), str(data_dir / 'seed.parquet'))
    os.remove(subset_csv)

    data_files = [
        {"path": "data/seed.parquet", "rows": rows, "size": size},
    ]

    # metadata.json
    table_uuid = str(uuid.uuid4())
    location = str(iceberg_dir.absolute())
    meta_dir = iceberg_dir / 'metadata'
    write_metadata_json(schema_fields, table_uuid, location, str(data_dir),
                        "metadata/snap-1.avro", str(meta_dir / 'metadata.json'))

    # manifest
    write_manifest_avro(data_files, str(meta_dir / 'snap-1.avro'))

    print(f"  Iceberg table ready at {iceberg_dir}", file=sys.stderr)


if __name__ == '__main__':
    main()
