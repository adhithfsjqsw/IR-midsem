"""PDF -> text for one year's tar archive. Usage: python -I -X utf8 scripts/extract.py 2019
Reads data/tar/<year>.tar (SC of India English judgments), writes data/text/<year>.jsonl
(one record per judgment: path, text). Extraction failures are counted, not hidden."""
import io, json, sys, tarfile
from multiprocessing import Pool
from pathlib import Path

import pymupdf as fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent


def pdf_to_text(args):
    name, data = args
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        pages = [p.get_text("text") for p in doc]
        return name, "\n".join(pages), None
    except Exception as e:  # corrupt pdf
        return name, "", repr(e)


def members(tar_path):
    with tarfile.open(tar_path) as tf:
        for m in tf:
            if m.isfile() and m.name.lower().endswith(".pdf"):
                yield Path(m.name).name, tf.extractfile(m).read()


def main(year):
    tar_path = ROOT / "data" / "tar" / f"{year}.tar"
    out_dir = ROOT / "data" / "text"
    out_dir.mkdir(parents=True, exist_ok=True)
    n = bad = 0
    with Pool(6) as pool, open(out_dir / f"{year}.jsonl", "w", encoding="utf-8") as out:
        for name, text, err in pool.imap_unordered(pdf_to_text, members(tar_path), chunksize=4):
            n += 1
            if err or len(text.split()) < 200:
                bad += 1
                continue
            out.write(json.dumps({"file": name, "text": text}, ensure_ascii=False) + "\n")
    print(f"{year}: {n} pdfs, {bad} dropped (error or <200 words), {n-bad} kept")


if __name__ == "__main__":
    main(sys.argv[1])

