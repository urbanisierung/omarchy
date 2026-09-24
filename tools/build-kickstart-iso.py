"""Prepare guided Fedora test media; never select or write a block device."""

import argparse
import hashlib
import json
import platform
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "installer/kickstart"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def digest(file_path):
    with file_path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(output, ref, iso=None, sha256=None):
    if output.exists() or output.is_symlink():
        raise ValueError(f"Refusing existing output path: {output}")
    if ref.startswith("-"):
        raise ValueError("Revision must not start with '-'.")
    revision = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected a full SHA-1 Git commit.")
    bootstrap = git("show", f"{revision}:boot.sh") + "\n"
    subprocess.run(["bash", "-n"], input=bootstrap, text=True, check=True)
    if iso is not None:
        if not iso.is_file() or iso.suffix.lower() != ".iso":
            raise ValueError("Input must be a regular .iso file, not a device.")
        if not sha256 or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
            raise ValueError("Supply --sha256 from Fedora's verified signed checksum.")
        if digest(iso) != sha256.lower():
            raise ValueError("Input ISO SHA256 mismatch.")

    output.mkdir(mode=0o700, parents=True)
    payload = output / "omarchy-usb"
    payload.mkdir()
    for name in ("setup.sh", "omarchy-usb-setup.desktop"):
        shutil.copyfile(ASSETS / name, payload / name)
    (payload / "boot.sh").write_text(bootstrap)
    (payload / "revision").write_text(revision + "\n")
    kickstart = output / "kickstart.ks"
    shutil.copyfile(ASSETS / "fedora44.ks", kickstart)
    manifest = {
        "fedora": 44,
        "architecture": "x86_64",
        "installer_commit": revision,
        "repository": "https://github.com/urbanisierung/omarchy.git",
        "source_iso": str(iso) if iso else None,
        "source_sha256": sha256.lower() if sha256 else None,
        "files": {
            str(item.relative_to(output)): digest(item)
            for item in sorted(output.rglob("*"))
            if item.is_file()
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return kickstart, payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="Committed installer revision")
    parser.add_argument("--output-dir", required=True, type=Path, help="New directory")
    parser.add_argument(
        "--iso", type=Path, help="Verified Fedora 44 Everything x86_64 ISO"
    )
    parser.add_argument(
        "--sha256", help="Expected input ISO checksum (not a signature)"
    )
    parser.add_argument(
        "--prepare-only", action="store_true", help="No privileged build"
    )
    args = parser.parse_args()
    try:
        if platform.machine() != "x86_64":
            raise ValueError("Build this x86_64 image on an x86_64 host.")
        if not args.prepare_only and args.iso is None:
            raise ValueError("A build requires --iso and --sha256.")
        if args.sha256 and args.iso is None:
            raise ValueError("--sha256 requires --iso.")
        if not args.prepare_only:
            for command in ("ksvalidator", "mkksiso", "sudo"):
                if shutil.which(command) is None:
                    raise ValueError(f"Missing {command}; see docs/kickstart-usb.md.")
        # Do not resolve the final component: dangling output symlinks must fail.
        output = args.output_dir.expanduser().absolute()
        iso = args.iso.expanduser().resolve() if args.iso else None
        kickstart, payload = prepare(output, args.ref, iso, args.sha256)
        if shutil.which("ksvalidator"):
            subprocess.run(["ksvalidator", "-v", "F44", str(kickstart)], check=True)
        else:
            print("NOT VALIDATED: install pykickstart and validate before building.")
        print(f"Prepared: {output}")
        print(
            "Ensure the pinned commit is pushed before installing on another machine."
        )
        if args.prepare_only:
            print("Preparation only: no ISO built, no disks written.")
            return 0
        image = output / "omarchy-fedora44-x86_64.iso"
        command = [
            "sudo",
            "-n",
            "mkksiso",
            "--ks",
            str(kickstart),
            "--add",
            str(payload),
            str(iso),
            str(image),
        ]
        print(shlex.join(command), flush=True)
        # Full EFI image handling needs root; never skip it to evade elevation.
        subprocess.run(command, check=True)
        (output / "SHA256SUMS").write_text(f"{digest(image)}  {image.name}\n")
        print(f"Built {image}. VM testing is required before USB use.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Stopped: {error}")
        print(
            "Retain any output for diagnosis; use a new output directory when retrying."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
