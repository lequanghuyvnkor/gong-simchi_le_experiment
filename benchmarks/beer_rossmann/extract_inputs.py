"""Extract the verified embedded ZIP from the user-supplied report; never execute it.

Requires pypdf in addition to Python 3.10+. Original PDF and embedded DOCX are
kept private; destination must not already exist.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    provenance = json.loads((Path(__file__).parent / "provenance.json").read_text())
    pdf = args.pdf.read_bytes()
    if hashlib.sha256(pdf).hexdigest() != provenance["source_pdf"]["sha256"]:
        parser.error("PDF SHA-256 differs from the supplied snapshot")
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf))
    name = provenance["embedded_zip"]["name"]
    files = reader.attachments[name]
    if len(files) != 1:
        parser.error("Expected exactly one embedded ZIP with the recorded name")
    raw = files[0]
    if hashlib.sha256(raw).hexdigest() != provenance["embedded_zip"]["sha256"]:
        parser.error("Embedded ZIP SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(i.file_size for i in archive.infolist()) > 500 * 1024 * 1024:
            parser.error("Archive exceeds the recorded extraction size limit")
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in info.filename
                    or ":" in info.filename or stat.S_ISLNK(info.external_attr >> 16)
                    or info.flag_bits & 1):
                parser.error(f"Unsafe archive entry: {info.filename}")
        args.destination.mkdir(parents=True, exist_ok=False)
        for info in archive.infolist():
            target = args.destination / info.filename
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
    print(json.dumps({"destination": str(args.destination.resolve()),
                      "embedded_zip_sha256": hashlib.sha256(raw).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
