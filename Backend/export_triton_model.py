import argparse
import json
from pathlib import Path


def build_triton_config(expected_feats: int) -> str:
    return f"""name: "tranad"
platform: "pytorch_libtorch"
max_batch_size: 0

input [
  {{
    name: "DATA"
    data_type: TYPE_FP32
    dims: [ -1, {expected_feats} ]
  }}
]

output [
  {{
    name: "SCORES"
    data_type: TYPE_FP32
    dims: [ -1 ]
  }}
]

instance_group [
  {{
    count: 1
    kind: KIND_AUTO
  }}
]

parameters: {{
  key: "DISABLE_OPTIMIZED_EXECUTION"
  value: {{ string_value: "true" }}
}}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the TranAD checkpoint as a Triton TorchScript model.")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "triton" / "model_repository" / "tranad" / "1"),
        help="Directory where model.pt and export metadata will be written.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    import sys

    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    from infer import export_triton_model
    sys.argv = original_argv

    export_info = export_triton_model(output_dir / "model.pt")
    manifest_path = output_dir.parent / "export_manifest.json"
    manifest_path.write_text(json.dumps(export_info, indent=2), encoding="utf-8")
    (output_dir.parent / "config.pbtxt").write_text(
        build_triton_config(export_info["expected_feats"]),
        encoding="utf-8",
    )

    print(json.dumps({"status": "ok", "manifest": str(manifest_path), **export_info}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
