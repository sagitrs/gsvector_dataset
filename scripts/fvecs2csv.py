#!/usr/bin/env python3
"""Convert .fvecs file to CSV format (PG COPY compatible).

Usage: python3 fvecs2csv.py <input.fvecs> <output.csv>
"""
import struct, sys, os

def fvecs_to_csv(in_path, out_path):
    with open(in_path, 'rb') as f:
        dim_bytes = f.read(4)
        if len(dim_bytes) < 4:
            print(f"ERROR: empty or truncated file: {in_path}", file=sys.stderr)
            sys.exit(1)
        dim = struct.unpack('<i', dim_bytes)[0]
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        vec_size = 4 + dim * 4
        count = file_size // vec_size

        print(f"  {in_path}: {count} vectors, dim={dim}", file=sys.stderr)

        f.seek(0)
        with open(out_path, 'w') as out:
            # header
            cols = ['id'] + [f'v{i}' for i in range(dim)]
            out.write(','.join(cols) + '\n')

            # data rows
            for i in range(count):
                f.read(4)  # skip dim prefix
                raw = f.read(dim * 4)
                vals = struct.unpack(f'<{dim}f', raw)
                out.write(str(i))
                for v in vals:
                    out.write(f',{v:.8g}')
                out.write('\n')

    out_size = os.path.getsize(out_path)
    print(f"  → {out_path}: {out_size:,} bytes", file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.fvecs> <output.csv>", file=sys.stderr)
        sys.exit(1)
    fvecs_to_csv(sys.argv[1], sys.argv[2])
