"""Load the PLOS and eLife lay summarisation datasets (Goldsack et al., EMNLP 2022).

Reads the authors' original JSON files directly instead of going through the
Hugging Face loader, because:
  * `tomasg25/scientific_lay_summarisation` is a script-based dataset, which
    recent versions of `datasets` no longer run;
  * the HF version merges the abstract into the `article` field and has no
    separate `abstract` column, while the raw JSON keeps abstract, lay summary
    and body text apart (each as a list of PySBD-segmented sentences).

The two archives are the ones the official HF loading script downloads.

Usage (from a notebook):
    from load_data import load_dataset
    plos = load_dataset("plos")    # DataFrame: one row per article
    elife = load_dataset("elife")
"""

from pathlib import Path
import tarfile
import zipfile

import gdown
import ijson
import pandas as pd

# Google Drive file IDs used by the official HF loading script
DRIVE_IDS = {
    "plos": "1lZ6PCAtXvmGjRZyp3vQQCEgO_yerH62Q",
    "elife": "1WKW8BAqluOlXrpy1B9mV3j3CtAK3JdnE",
}
SPLIT_FILES = {"train": "train.json", "validation": "val.json", "test": "test.json"}
DATA_DIR = Path("data")


def download(dataset: str, data_dir: Path = DATA_DIR) -> Path:
    """Download and extract one dataset archive (skipped if already done)."""
    out_dir = data_dir / dataset
    if out_dir.exists() and any(out_dir.rglob("*.json")):
        return out_dir

    data_dir.mkdir(parents=True, exist_ok=True)
    archive = data_dir / f"{dataset}.archive"
    if not archive.exists():
        # If Google Drive refuses (quota errors happen), download the file
        # manually in a browser from
        # https://drive.google.com/uc?id=<DRIVE_IDS[dataset]>
        # and save it as data/<dataset>.archive
        gdown.download(id=DRIVE_IDS[dataset], output=str(archive), quiet=False)

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(out_dir)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            tf.extractall(out_dir)
    else:
        raise ValueError(f"{archive} is neither a zip nor a tar archive")
    return out_dir


def _find(out_dir: Path, filename: str) -> Path:
    """Locate a split file anywhere inside the extracted archive."""
    matches = [p for p in out_dir.rglob(filename) if "__MACOSX" not in p.parts]
    if not matches:
        raise FileNotFoundError(f"No {filename} found under {out_dir}")
    return matches[0]


def load_split(dataset: str, split: str, data_dir: Path = DATA_DIR,
               keep_article: bool = False) -> pd.DataFrame:
    """Load one split, streaming the JSON so the full file never sits in RAM.

    Columns: dataset, split, id, abstract, summary, n_abstract_sents,
    n_summary_sents (+ article if keep_article=True).
    The article text EXCLUDES the abstract, with sections joined by newlines.
    """
    path = _find(download(dataset, data_dir), SPLIT_FILES[split])
    rows = []
    with open(path, "rb") as f:
        for d in ijson.items(f, "item"):  # file is one JSON list of articles
            row = {
                "dataset": dataset,
                "split": split,
                "id": d["id"],
                "abstract": " ".join(d["abstract"]).strip(),
                "summary": " ".join(d["summary"]).strip(),
                "n_abstract_sents": len(d["abstract"]),
                "n_summary_sents": len(d["summary"]),
            }
            if keep_article:
                row["article"] = "\n".join(" ".join(s).strip() for s in d["sections"])
            rows.append(row)
    return pd.DataFrame(rows)


def load_dataset(dataset: str, data_dir: Path = DATA_DIR,
                 keep_article: bool = False, use_cache: bool = True) -> pd.DataFrame:
    """Load all three splits of `dataset` ("plos" or "elife") as one DataFrame.

    The parsed result is cached to data/<dataset>[_with_article].parquet,
    so the large JSON files are only parsed once.
    """
    suffix = "_with_article" if keep_article else ""
    cache = data_dir / f"{dataset}{suffix}.parquet"
    if use_cache and cache.exists():
        return pd.read_parquet(cache)

    df = pd.concat(
        [load_split(dataset, s, data_dir, keep_article) for s in SPLIT_FILES],
        ignore_index=True,
    )
    if use_cache:
        df.to_parquet(cache, index=False)
    return df
