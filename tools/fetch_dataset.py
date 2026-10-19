"""Download a few patients from the NLM "Thick Smears 150" dataset into data/.

The dataset is a single ~3.9 GB zip. NLM's server supports HTTP range
requests, so we open the zip remotely and pull only the files we need.

Usage:
    python tools/fetch_dataset.py --list            # show folder layout
    python tools/fetch_dataset.py --patients 12     # fetch the first 12 patients
"""
import argparse
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://data.lhncbc.nlm.nih.gov/public/Malaria/Thick_Smears_150/ThickBloodSmears_150.zip"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "nlm_thick"


class HttpRangeFile(io.RawIOBase):
    """A read-only, seekable file object backed by HTTP range requests."""

    def __init__(self, url):
        self.url = url
        self.pos = 0
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as resp:
            self.size = int(resp.headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        else:
            self.pos = self.size + offset
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.pos + n, self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        self.pos += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[: len(data)] = data
        return len(data)


def open_remote_zip():
    return zipfile.ZipFile(io.BufferedReader(HttpRangeFile(URL), buffer_size=1 << 20))


def patient_of(name):
    """Images live in <patient>/<file>.jpg, annotations in GT_updated/<patient>/<file>.txt."""
    parts = [p for p in name.split("/") if p]
    if len(parts) == 3 and parts[0] == "GT_updated":
        return parts[1]
    if len(parts) == 2 and parts[1].lower().endswith(".jpg"):
        return parts[0]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print the zip layout and exit")
    ap.add_argument("--patients", type=int, default=12)
    ap.add_argument("--only", nargs="*", help="explicit patient folder names")
    args = ap.parse_args()

    zf = open_remote_zip()
    names = [n for n in zf.namelist() if not n.endswith("/")]

    if args.list:
        for n in names[:60]:
            print(n)
        print(f"... {len(names)} files")
        return

    images_per_patient = {}
    for n in names:
        if n.lower().endswith(".jpg") and patient_of(n):
            images_per_patient[patient_of(n)] = images_per_patient.get(patient_of(n), 0) + 1
    # Prefer patients with many fields: sample mode needs enough fields to reach 200 WBC.
    patients = sorted(images_per_patient, key=lambda p: (-images_per_patient[p], p))
    chosen = args.only or patients[: args.patients]
    print(f"{len(patients)} patients in archive; fetching {len(chosen)}")
    for name in names:
        if patient_of(name) not in chosen:
            continue
        target = DATA_DIR / name
        if target.exists() and target.stat().st_size == zf.getinfo(name).file_size:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(zf.read(name))
        print("  ", name)
    print("done ->", DATA_DIR)


if __name__ == "__main__":
    sys.exit(main())
