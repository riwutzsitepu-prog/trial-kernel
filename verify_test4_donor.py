#!/usr/bin/env python3
import argparse
import hashlib
import struct
from pathlib import Path

TAIL_SIZE = 2092004
TAIL_SHA256 = "8eb391b228f59ffc98885fcb2101cc2f49965de3e7e4aba5ba864158e43b31e1"
EXPECTED = [
    ("arch/arm64/boot/dts/qcom/msm8992-bullhead-rev-101.dtb", 5306, "daac83fa3cf8e5ca0bc4a387cb830dd3021151197f9d60ea438c53ac546dd640"),
    ("arch/arm64/boot/dts/qcom/sa6155p.dtb", 373645, "7a3bacfbaca1a5a0e7a3687094ef6b62640ac63b05c6f0eb145f0d19c19315c5"),
    ("arch/arm64/boot/dts/qcom/sdmmagpie.dtb", 398315, "9d0c45d1f03ce820e1e1480d00e4a645d8b0fc27a404d57280e8f12d8de89233"),
    ("arch/arm64/boot/dts/qcom/apq8096-db820c.dtb", 33269, "073fb1995bc30c53d9db6f0a702b8c9e61a1bf626cea7e23f33a5d7a29db5c42"),
    ("arch/arm64/boot/dts/qcom/apq8016-sbc.dtb", 54743, "b9157f69ca534ee022aeab18f00fc61b345c06372189af7cad1c7bf84ece04c1"),
    ("arch/arm64/boot/dts/qcom/msm8996-mtp.dtb", 27379, "1cb26c9a5b46ce04f4d750f2442770eca00cddf365df96cbe220640e338acc3a"),
    ("arch/arm64/boot/dts/qcom/msm8916-mtp.dtb", 46749, "75df380a33f37803e360c7c25f181ae57a4dacdd6e1e22061470edbef0f76b97"),
    ("arch/arm64/boot/dts/qcom/msm8994-angler-rev-101.dtb", 4753, "aef4a1c033c98c54dfc3dbe54d18c13babe7573eb6aa04862ee7af1070832151"),
    ("arch/arm64/boot/dts/qcom/sa6155.dtb", 360792, "3b749ca29e462a7f89a04912dc2db740a959570df2d18679984462c3b24bc998"),
    ("arch/arm64/boot/dts/qcom/sm6150.dtb", 391492, "9bd7d4dd0744f8ef36989eb9333c5ea3c66779a415edd02b12e4c15208c11ae9"),
    ("arch/arm64/boot/dts/qcom/ipq8074-hk01.dtb", 4065, "c870adec605c0109630d34f4f5207655c09bdb58f382278f5891587faa8955c6"),
    ("arch/arm64/boot/dts/qcom/sm6150p.dtb", 391496, "c8270c5639d3a97f776b2d3e3ebd922dc8493b956d5d72c59913d20e2a39d417"),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tail")
    ap.add_argument("--kernel-src")
    ap.add_argument("--out-dir")
    ap.add_argument("--report")
    args = ap.parse_args()

    tail = Path(args.tail).read_bytes()
    if len(tail) != TAIL_SIZE:
        raise SystemExit(f"tail size mismatch: {len(tail)} != {TAIL_SIZE}")
    actual_tail_sha = sha256(tail)
    if actual_tail_sha != TAIL_SHA256:
        raise SystemExit(f"tail sha mismatch: {actual_tail_sha} != {TAIL_SHA256}")

    out_dir = Path(args.out_dir) if args.out_dir else None
    kernel_src = Path(args.kernel_src) if args.kernel_src else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    pos = 0
    rows = []
    for i, (name, exp_size, exp_sha) in enumerate(EXPECTED):
        if pos + 8 > len(tail):
            raise SystemExit(f"FDT {i}: truncated header")
        magic, total = struct.unpack(">II", tail[pos:pos+8])
        if magic != 0xD00DFEED:
            raise SystemExit(f"FDT {i}: bad magic 0x{magic:08x} at {pos}")
        if total != exp_size:
            raise SystemExit(f"FDT {i}: size {total} != {exp_size}")
        if pos + total > len(tail):
            raise SystemExit(f"FDT {i}: extends past tail")
        blob = tail[pos:pos+total]
        actual_sha = sha256(blob)
        if actual_sha != exp_sha:
            raise SystemExit(f"FDT {i}: sha {actual_sha} != {exp_sha}")
        if out_dir:
            (out_dir / f"{i:02d}.dtb").write_bytes(blob)
        if kernel_src:
            dst = kernel_src / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(blob)
        rows.extend([
            f"FDT_{i:02d}_OFFSET={pos}",
            f"FDT_{i:02d}_SIZE={total}",
            f"FDT_{i:02d}_SHA256={actual_sha}",
        ])
        pos += total

    if len(EXPECTED) != 12 or pos != len(tail):
        raise SystemExit(f"FDT parse mismatch: count={len(EXPECTED)} leftover={len(tail)-pos}")

    report = "\n".join([
        "FDT_VALIDATION=PASS",
        "FDT_PARSE=PASS",
        "FDT_COUNT=12",
        "FDT_LEFTOVER_BYTES=0",
        f"DONOR_TAIL_SIZE={len(tail)}",
        f"DONOR_TAIL_SHA256={actual_tail_sha}",
        *rows,
        "",
    ])
    if args.report:
        Path(args.report).write_text(report)
    print(report, end="")


if __name__ == "__main__":
    main()
