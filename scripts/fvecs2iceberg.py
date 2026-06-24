#!/usr/bin/env python3
"""Convert .fvecs files to Iceberg table format.

Generates: Parquet data files + metadata.json + manifest list (Avro).

Usage: python3 fvecs2iceberg.py --base <base.fvecs> --query <query.fvecs> --out-dir <dir>
"""
import argparse, json, os, struct, sys, time, uuid
from pathlib import Path

def read_fvecs(path):
    """Return (vectors, dim) as list of float lists."""
    vectors = []
    dim = 0
    with open(path, 'rb') as f:
        size = os.fstat(f.fileno()).st_size
        while f.tell() < size:
            d_bytes = f.read(4)
            if len(d_bytes) < 4:
                break
            d = struct.unpack('<i', d_bytes)[0]
            if dim == 0:
                dim = d
            elif d != dim:
                raise ValueError(f"Mismatched dim in {path}: {d} vs {dim}")
            raw = f.read(dim * 4)
            if len(raw) < dim * 4:
                break
            vectors.append(list(struct.unpack(f'<{dim}f', raw)))
    return vectors, dim


def build_schema(dim):
    """Return Iceberg schema fields JSON."""
    fields = [{"id": 1, "name": "id", "type": "long", "required": True}]
    for i in range(dim):
        fields.append({"id": i + 2, "name": f"v{i}",
                       "type": "float", "required": True})
    return fields


def write_parquet(vectors, dim, out_path):
    """Write vectors as Parquet file with id + v0..v{d-1} columns."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("ERROR: pyarrow required. pip install pyarrow", file=sys.stderr)
        sys.exit(1)

    cols = {"id": pa.array(range(len(vectors)), type=pa.int64())}
    for i in range(dim):
        cols[f"v{i}"] = pa.array([v[i] for v in vectors], type=pa.float32())

    table = pa.table(cols)
    pq.write_table(table, out_path)
    print(f"  → {out_path}: {table.num_rows} rows, {table.num_columns} cols", file=sys.stderr)


def write_metadata_json(dim, table_uuid, location, data_dir, manifest_rel, out_path):
    """Write minimal Iceberg metadata.json."""
    schema_fields = build_schema(dim)
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
    """Write a minimal Iceberg manifest list in Avro format.
    Falls back to stub if fastavro is not installed."""
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
        # stub: write minimal binary (gsiceberg manifest_avro.c handles graceful failure)
        with open(out_path, 'wb') as f:
            f.write(b'\x00' * 4)  # minimal stub
        print(f"  → {out_path} (stub, install fastavro for full)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="fvecs → Iceberg table converter")
    parser.add_argument('--base', required=True, help='Base .fvecs file')
    parser.add_argument('--query', required=True, help='Query .fvecs file')
    parser.add_argument('--out-dir', required=True, help='Output dataset dir (e.g. sift/1k)')
    parser.add_argument('--table-name', default=None, help='Table name (default: derived from dir)')
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    iceberg_dir = out_dir / 'iceberg'

    base_vecs, dim = read_fvecs(args.base)
    query_vecs, _ = read_fvecs(args.query)

    print(f"  base: {len(base_vecs)} x {dim}, query: {len(query_vecs)}", file=sys.stderr)

    # Parquet data
    data_dir = iceberg_dir / 'data'
    os.makedirs(data_dir, exist_ok=True)
    write_parquet(base_vecs, dim, str(data_dir / 'base.parquet'))
    write_parquet(query_vecs, dim, str(data_dir / 'query.parquet'))

    data_files = [
        {"path": "data/base.parquet", "rows": len(base_vecs),
         "size": os.path.getsize(data_dir / 'base.parquet')},
        {"path": "data/query.parquet", "rows": len(query_vecs),
         "size": os.path.getsize(data_dir / 'query.parquet')},
    ]

    # metadata.json
    table_uuid = str(uuid.uuid4())
    location = str(iceberg_dir.absolute())
    meta_dir = iceberg_dir / 'metadata'
    write_metadata_json(dim, table_uuid, location, str(data_dir),
                        "metadata/snap-1.avro", str(meta_dir / 'metadata.json'))

    # manifest
    write_manifest_avro(data_files, str(meta_dir / 'snap-1.avro'))

    print(f"  Iceberg table ready at {iceberg_dir}", file=sys.stderr)


if __name__ == '__main__':
    main()
