from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import tomllib
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ManifestMethod = Literal["http", "yt-dlp", "generated"]


@dataclass(frozen=True, slots=True)
class ClipSpec:
    id: str
    tier: str
    method: ManifestMethod
    local_path: Path
    intended_use: str
    download_url: str | None = None
    download_command: str | None = None
    needs_local_encode: bool = False
    expected_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class DerivedEncode:
    id: str
    video_codec: str
    preset: str
    crf: int
    gop: int
    pixel_format: str


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    clips: tuple[ClipSpec, ...]
    derived_encodes: tuple[DerivedEncode, ...]


def _load_manifest(path: Path) -> CorpusManifest:
    payload = tomllib.loads(path.read_text())
    raw_clips = payload.get("clip", [])
    raw_encodes = payload.get("derived_encode", [])
    clips = tuple(_parse_clip(raw_clip) for raw_clip in raw_clips)
    derived_encodes = tuple(_parse_derived_encode(raw_encode) for raw_encode in raw_encodes)
    return CorpusManifest(clips=clips, derived_encodes=derived_encodes)


def _parse_clip(raw_clip: Any) -> ClipSpec:
    if not isinstance(raw_clip, dict):
        raise ValueError(f"clip entry must be a table, got {type(raw_clip)!r}")
    raw_method = raw_clip.get("method")
    if raw_method not in {"http", "yt-dlp", "generated"}:
        raise ValueError(f"unsupported clip method: {raw_method!r}")
    raw_path = raw_clip.get("local_path")
    if not isinstance(raw_path, str):
        raise ValueError(f"clip local_path must be a string, got {raw_path!r}")
    return ClipSpec(
        id=_expect_str(raw_clip, "id"),
        tier=_expect_str(raw_clip, "tier"),
        method=raw_method,
        local_path=Path(raw_path),
        intended_use=_expect_str(raw_clip, "intended_use"),
        download_url=_optional_str(raw_clip, "download_url"),
        download_command=_optional_str(raw_clip, "download_command"),
        needs_local_encode=bool(raw_clip.get("needs_local_encode", False)),
        expected_sha256=_optional_str(raw_clip, "expected_sha256"),
    )


def _parse_derived_encode(raw_encode: Any) -> DerivedEncode:
    if not isinstance(raw_encode, dict):
        raise ValueError(f"derived_encode entry must be a table, got {type(raw_encode)!r}")
    return DerivedEncode(
        id=_expect_str(raw_encode, "id"),
        video_codec=_expect_str(raw_encode, "video_codec"),
        preset=_expect_str(raw_encode, "preset"),
        crf=_expect_int(raw_encode, "crf"),
        gop=_expect_int(raw_encode, "gop"),
        pixel_format=_expect_str(raw_encode, "pixel_format"),
    )


def _expect_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"expected non-empty string for {key}, got {value!r}")
    return value


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"expected optional string for {key}, got {value!r}")
    return value


def _expect_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"expected int for {key}, got {value!r}")
    return value


def _run(command: list[str], *, dry_run: bool) -> None:
    print("$", " ".join(shlex.quote(part) for part in command))
    if dry_run:
        return
    subprocess.run(command, check=True)


def _download_http(url: str, destination: Path, *, force: bool, dry_run: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        print(f"skip existing {destination}")
        return
    print(f"download {url} -> {destination}")
    if dry_run:
        return
    with urllib.request.urlopen(url) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def _download_crosscheck(command_text: str, *, dry_run: bool) -> None:
    command = shlex.split(command_text)
    if not command:
        raise ValueError("empty cross-check download command")
    _run(command, dry_run=dry_run)


def _encode_clip(source: Path, encode: DerivedEncode, *, force: bool, dry_run: bool) -> None:
    if not source.exists() and not dry_run:
        raise FileNotFoundError(f"cannot encode missing source clip: {source}")
    output_name = f"{source.stem}_{encode.id}.mp4"
    destination = Path("data/corpus/derived") / output_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        print(f"skip existing {destination}")
        return
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-c:v",
        encode.video_codec,
        "-preset",
        encode.preset,
        "-crf",
        str(encode.crf),
        "-g",
        str(encode.gop),
        "-pix_fmt",
        encode.pixel_format,
        str(destination),
    ]
    _run(command, dry_run=dry_run)


def _selected_clips(
    manifest: CorpusManifest,
    *,
    tiers: set[str],
    clip_ids: set[str],
) -> list[ClipSpec]:
    selected: list[ClipSpec] = []
    for clip in manifest.clips:
        if tiers and clip.tier not in tiers:
            continue
        if clip_ids and clip.id not in clip_ids:
            continue
        selected.append(clip)
    return selected


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch or generate local corpus assets.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/corpus/manifest.toml"),
        help="Path to the corpus manifest.",
    )
    parser.add_argument(
        "--tier",
        action="append",
        default=[],
        help="Tier(s) to fetch, for example: primary, crosscheck, synthetic.",
    )
    parser.add_argument(
        "--clip-id",
        action="append",
        default=[],
        help="Specific clip id(s) to fetch.",
    )
    parser.add_argument(
        "--encode",
        action="store_true",
        help="Encode derived H.264 assets for primary raw clips after download.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing local files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without executing them.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    manifest = _load_manifest(args.manifest)
    tiers = set(args.tier)
    clip_ids = set(args.clip_id)
    selected = _selected_clips(manifest, tiers=tiers, clip_ids=clip_ids)
    if not selected:
        raise SystemExit("no matching clips selected")

    for clip in selected:
        if clip.method == "http":
            if clip.download_url is None:
                raise ValueError(f"http clip {clip.id} is missing download_url")
            _download_http(
                clip.download_url, clip.local_path, force=args.force, dry_run=args.dry_run
            )
            if args.encode and clip.needs_local_encode:
                for encode in manifest.derived_encodes:
                    _encode_clip(clip.local_path, encode, force=args.force, dry_run=args.dry_run)
        elif clip.method == "yt-dlp":
            if clip.download_command is None:
                raise ValueError(f"yt-dlp clip {clip.id} is missing download_command")
            _download_crosscheck(clip.download_command, dry_run=args.dry_run)
        elif clip.method == "generated":
            print(
                f"{clip.id}: generated asset, use "
                "'uv run python scripts/generate_synthetic_corpus.py' instead"
            )
        else:
            raise ValueError(f"unsupported clip method: {clip.method!r}")


if __name__ == "__main__":
    main()
