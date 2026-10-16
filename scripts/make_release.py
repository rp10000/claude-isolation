#!/usr/bin/env python3
"""Build an allowlisted ZIP; never include generated settings, exports or logs."""
import argparse
import hashlib
from pathlib import Path
import zipfile

FILES = (
    "SKILL.md", "README.md", "LICENSE", ".gitignore", "agents/openai.yaml",
    "assets/example-config.json", "scripts/generate.py", "scripts/windows-guard.ps1",
    "scripts/make_release.py", "references/generator.md", "references/windows.md",
    "references/macos.md", "references/proxy-clients.md", "references/ikuai.md",
    "references/verification.md", "tests/test_generate.py", "tests/test_windows.py",
    "tests/test_windows_mock.ps1", "tests/test_release.py", "THIRD-PARTY-NOTICES.md",
    "assets/public_suffix_list.dat", "assets/MPL-2.0.txt",
)


def package(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if root == output or root in output.parents:
        raise ValueError("Release ZIP must be outside the skill source folder")
    checksum = output.with_name(output.name + ".sha256")
    if output.exists() or checksum.exists():
        raise FileExistsError("ZIP/checksum already exists; choose a fresh output path")
    if not output.parent.is_dir():
        raise ValueError("Output parent directory must exist")
    contents = {}
    for relative in FILES:
        source = root / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing or symlinked release source: {relative}")
        if root not in source.resolve().parents:
            raise ValueError("Release source escaped its root")
        contents[relative] = source.read_bytes()
        contents[relative].decode("utf-8")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, data in contents.items():
            entry = zipfile.ZipInfo("claude-isolation/" + relative, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    with checksum.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(f"{digest}  {output.name}\n")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        digest = package(Path(__file__).resolve().parents[1], args.out)
    except (OSError, ValueError) as error:
        parser.exit(2, f"Packaging refused: {error}\n")
    print(f"Created ZIP and SHA256; {len(FILES)} source files. SHA256: {digest}")


if __name__ == "__main__":
    main()
