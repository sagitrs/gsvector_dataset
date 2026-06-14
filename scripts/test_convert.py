#!/usr/bin/env python3
"""
Verify fbin/ibin → fvecs/ivecs conversion roundtrip.

Generates synthetic data, converts through convert_fbin.py, and
validates bit-exact recovery.  No external dependencies beyond
numpy and the conversion script.
"""

import os
import struct
import sys
import tempfile
import numpy as np

# Add scripts dir to path for import
sys.path.insert(0, os.path.dirname(__file__))
from convert_fbin import read_fbin, read_ibin, write_fvecs, write_ivecs


def test_fbin_roundtrip():
    """Generate fbin → fvecs → read back → compare."""
    np.random.seed(42)
    N, dim = 100, 128
    original = np.random.randn(N, dim).astype(np.float32)

    with tempfile.TemporaryDirectory() as tmp:
        # Write fbin
        fbin_path = os.path.join(tmp, "test.fbin")
        with open(fbin_path, "wb") as f:
            f.write(struct.pack("<I", N))
            f.write(struct.pack("<I", dim))
            f.write(original.tobytes())

        # Read via fbin reader
        data = read_fbin(fbin_path)
        assert data.shape == (N, dim), f"Shape mismatch: {data.shape}"
        assert np.allclose(data, original), "Data mismatch"

        # Write as fvecs
        fvecs_path = os.path.join(tmp, "test.fvecs")
        write_fvecs(fvecs_path, data)

        # Read fvecs back manually
        with open(fvecs_path, "rb") as f:
            raw = f.read()
        recovered = []
        off = 0
        while off < len(raw):
            d = struct.unpack_from("<i", raw, off)[0]
            off += 4
            vec = np.frombuffer(raw, dtype=np.float32, count=d, offset=off)
            recovered.append(vec)
            off += d * 4
        recovered = np.stack(recovered)
        assert recovered.shape == (N, dim)
        assert np.allclose(recovered, original)

    print("PASS: test_fbin_roundtrip")


def test_ibin_roundtrip():
    """Generate ibin → ivecs → read back → compare."""
    np.random.seed(123)
    Q, k = 50, 10
    max_id = 1000
    original = np.random.randint(0, max_id, size=(Q, k)).astype(np.int32)

    with tempfile.TemporaryDirectory() as tmp:
        # Write ibin
        ibin_path = os.path.join(tmp, "test.ibin")
        with open(ibin_path, "wb") as f:
            f.write(struct.pack("<I", Q))
            f.write(struct.pack("<I", k))
            f.write(original.tobytes())

        # Read via ibin reader
        data = read_ibin(ibin_path)
        assert data.shape == (Q, k)
        assert np.array_equal(data, original), "Data mismatch"

        # Write as ivecs
        ivecs_path = os.path.join(tmp, "test.ivecs")
        write_ivecs(ivecs_path, data)

        # Read ivecs back manually
        with open(ivecs_path, "rb") as f:
            raw = f.read()
        recovered = []
        off = 0
        while off < len(raw):
            d = struct.unpack_from("<i", raw, off)[0]
            off += 4
            indices = np.frombuffer(raw, dtype=np.int32, count=d, offset=off)
            recovered.append(indices)
            off += d * 4
        recovered = np.stack(recovered)
        assert recovered.shape == (Q, k)
        assert np.array_equal(recovered, original)

    print("PASS: test_ibin_roundtrip")


def test_convert_cli():
    """Test the CLI interface of convert_fbin.py."""
    np.random.seed(99)
    N, dim = 50, 64
    Q, k = 10, 10

    base = np.random.randn(N, dim).astype(np.float32)
    query = np.random.randn(Q, dim).astype(np.float32)
    gt = np.random.randint(0, N, size=(Q, 100)).astype(np.int32)

    with tempfile.TemporaryDirectory() as tmp:
        # Write input files
        base_fbin = os.path.join(tmp, "base.fbin")
        query_fbin = os.path.join(tmp, "query.fbin")
        gt_ibin = os.path.join(tmp, "gt.ibin")
        out_dir = os.path.join(tmp, "out")

        with open(base_fbin, "wb") as f:
            f.write(struct.pack("<I", N))
            f.write(struct.pack("<I", dim))
            f.write(base.tobytes())
        with open(query_fbin, "wb") as f:
            f.write(struct.pack("<I", Q))
            f.write(struct.pack("<I", dim))
            f.write(query.tobytes())
        with open(gt_ibin, "wb") as f:
            f.write(struct.pack("<I", Q))
            f.write(struct.pack("<I", 100))
            f.write(gt.tobytes())

        # Run converter
        cmd = (f"{sys.executable} {os.path.join(os.path.dirname(__file__), 'convert_fbin.py')} "
               f"--base {base_fbin} --query {query_fbin} "
               f"--gt-neighbors {gt_ibin} --out-dir {out_dir}")
        ret = os.system(cmd)
        assert ret == 0, f"convert_fbin.py exited with {ret}"

        # Verify base.fvecs
        base_fvecs = os.path.join(out_dir, "base.fvecs")
        assert os.path.exists(base_fvecs)
        with open(base_fvecs, "rb") as f:
            raw = f.read()
        recovered = []
        off = 0
        while off < len(raw):
            d = struct.unpack_from("<i", raw, off)[0]
            off += 4
            recovered.append(np.frombuffer(raw, dtype=np.float32, count=d, offset=off))
            off += d * 4
        recovered = np.stack(recovered)
        assert np.allclose(recovered, base)

        # Verify gt_top10.ivecs
        gt10_fvecs = os.path.join(out_dir, "gt_top10.ivecs")
        assert os.path.exists(gt10_fvecs)
        with open(gt10_fvecs, "rb") as f:
            raw = f.read()
        recovered = []
        off = 0
        while off < len(raw):
            d = struct.unpack_from("<i", raw, off)[0]
            off += 4
            recovered.append(np.frombuffer(raw, dtype=np.int32, count=d, offset=off))
            off += d * 4
        recovered = np.stack(recovered)
        assert recovered.shape == (Q, 10)
        assert np.array_equal(recovered, gt[:, :10])

    print("PASS: test_convert_cli")


def test_fvecs_ivecs_deterministic():
    """Same input → same output (no randomness)."""
    np.random.seed(1)
    N, dim = 20, 16
    base = np.random.randn(N, dim).astype(np.float32)

    with tempfile.TemporaryDirectory() as tmp:
        out1 = os.path.join(tmp, "out1")
        out2 = os.path.join(tmp, "out2")
        os.makedirs(out1, exist_ok=True)
        os.makedirs(out2, exist_ok=True)

        write_fvecs(os.path.join(out1, "base.fvecs"), base)
        write_fvecs(os.path.join(out2, "base.fvecs"), base)

        with open(os.path.join(out1, "base.fvecs"), "rb") as f:
            d1 = f.read()
        with open(os.path.join(out2, "base.fvecs"), "rb") as f:
            d2 = f.read()
        assert d1 == d2, "Deterministic output mismatch"

    print("PASS: test_fvecs_ivecs_deterministic")


if __name__ == "__main__":
    failures = 0
    for test in [test_fbin_roundtrip, test_ibin_roundtrip,
                 test_convert_cli, test_fvecs_ivecs_deterministic]:
        try:
            test()
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failures += 1

    if failures == 0:
        print("\nAll tests passed.")
    else:
        print(f"\n{failures} test(s) failed.")
        sys.exit(1)
