"""Full public raw data (D1, interim): the test sample's layout, with the public sources it truncates downloaded in full.

Copies the sample (tests/test_macro_data/unit/sample_raw_data) to <datasets>/macro_raw_data, then replaces:
- the OECD input-output tables (ICIO 2023 edition, small version, 76 countries + ROW): 2011-2017; 2010 when the
  2006-2010 bundle is in <datasets>/downloads/icio (its download link sits behind a browser check, so fetch it by
  hand from https://oe.cd/icio);
- the Eurostat series the sample cuts to France (quarterly GDP, chain-linked volumes, deflators, unemployment) or to
  2014 (financial balance sheets), now all countries;
- OECD house prices (France only in the sample), now all countries.
Everything else is the sample's copy. HFCS (households) and Compustat (firms, banks) stay the sample's SPOOFED files
until the licensed micro-data arrives (PROJECT.md, Data). SOURCES.json in the output records what each file is.

    uv run python experiments/public_data.py [--datasets DIR]    # or: make data
"""

import argparse
import json
import shutil
import subprocess
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests/test_macro_data/unit/sample_raw_data"
DATASETS = Path("~/Documents/dev/phd/datasets").expanduser()
ICIO_YEARS = range(2010, 2018)
# OECD ICIO 2023 edition, small version (China and Mexico not split), five-year bundles of {year}_SML.csv
ICIO_BUNDLES = {
    "2006-2010": "https://webfs-sti.oecd.org/files/STI-PIE/ICIO/2023/2006-2010_SML.zip",
    "2011-2015": "https://stats.oecd.org/wbos/fileview2.aspx?IDFile=1f791bc6-befb-45c5-8b34-668d08a1702a",
    "2016-2020": "https://stats.oecd.org/wbos/fileview2.aspx?IDFile=d1ab2315-298c-4e93-9a81-c6f2273139fe",
}
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"
# file -> (dataflow, key with every country, first period, last period), as SDMX-CSV
EUROSTAT_SERIES = {
    "namq_10_gdp": ("namq_10_gdp", "Q.CP_MNAC.SCA.B1GQ.", "1995-Q1", "2023-Q4"),
    "namq_10_gdp_clv": ("namq_10_gdp", "Q.CLV10_MEUR.SCA.B1GQ+P31_S14_S15+P31_S14+P3_S13+P51G.", "1995-Q1", "2023-Q4"),
    "namq_10_gdp_deflators": ("namq_10_gdp", "Q.PD10_EUR.SCA.B1GQ+P31_S14_S15.", "1995-Q1", "2023-Q4"),
    "une_rt_q": ("une_rt_q", "Q.SA.Y15-74.PC_ACT.T.", "1995-Q1", "2023-Q4"),
}
HOUSE_PRICES = (
    "https://sdmx.oecd.org/public/rest/data/OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES,/.Q.RHP+HPI."
    "?startPeriod=1970-Q1&format=csvfilewithlabels"
)
SPOOFED = ["hfcs", "compustat"]


def fetch(url: str, path: Path) -> Path:
    """Download url to path once; later runs reuse the file. curl, since it uses the system's certificates."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(path.suffix + ".part")
        subprocess.run(["curl", "-sSfL", "-A", "Mozilla/5.0", "-o", str(partial), url], check=True)
        partial.rename(path)
    return path


def copy_sample(out: Path) -> None:
    # icio/2014/ holds the 2021 edition, which no reader uses; *_SML_P.csv are pivot caches of the sample's tables
    def ignore(directory: str, names: list[str]) -> list[str]:
        unused = ["2014"] if Path(directory) == SAMPLE / "icio" else []
        return [n for n in names if n in unused or n.endswith("_SML_P.csv")]

    shutil.copytree(SAMPLE, out, dirs_exist_ok=True, ignore=ignore)


def icio(downloads: Path, out: Path) -> dict[str, str]:
    sources = {}
    for bundle, url in ICIO_BUNDLES.items():
        first, last = (int(y) for y in bundle.split("-"))
        years = [y for y in ICIO_YEARS if first <= y <= last]
        if not years:
            continue
        zip_path = downloads / "icio" / f"{bundle}_SML.zip"
        try:
            fetch(url, zip_path)
        except subprocess.CalledProcessError as error:
            print(
                f"ICIO {bundle}: not downloaded ({error}); fetch {bundle}_SML.zip from https://oe.cd/icio into {zip_path}"
            )
            continue
        with zipfile.ZipFile(zip_path) as bundle_zip:
            for year in years:
                (out / "icio" / f"{year}_SML.csv").write_bytes(bundle_zip.read(f"{year}_SML.csv"))
                # the reader caches its pivot of the table next to it; a stale cache would hide the new table
                (out / "icio" / f"{year}_SML_P.csv").unlink(missing_ok=True)
                sources[f"icio/{year}_SML.csv"] = f"public, full: OECD ICIO 2023 edition, small version ({url})"
    return sources


def eurostat(downloads: Path, out: Path) -> dict[str, str]:
    sources = {}
    for name, (flow, key, start, end) in EUROSTAT_SERIES.items():
        url = f"{EUROSTAT}/{flow}/{key}/?format=SDMX-CSV&startPeriod={start}&endPeriod={end}"
        shutil.copyfile(fetch(url, downloads / "eurostat" / f"{name}.csv"), out / "eurostat" / f"{name}.csv")
        sources[f"eurostat/{name}.csv"] = f"public, full: {url}"

    # Financial balance sheets in the layout the reader parses: Eurostat's old bulk format, one column per year,
    # values as text with an optional flag ("123.4 b"), ":" when missing. One request per sector: Eurostat queues
    # a request for the whole table as an asynchronous job instead of answering it
    sample = pd.read_csv(SAMPLE / "eurostat" / "nasa_10_f_bs.csv", usecols=[0]).iloc[:, 0]
    url = f"{EUROSTAT}/nasa_10_f_bs/A.MIO_NAC.NCO.{{sector}}.../?format=TSV&compressed=false&startPeriod=2005"
    parts = []
    for sector in sorted(sample.str.split(",").str[2].unique()):
        path = fetch(url.format(sector=sector), downloads / "eurostat" / "nasa_10_f_bs" / f"{sector}.tsv")
        if path.read_text().startswith("<?xml"):
            path.unlink()
            raise RuntimeError(f"Eurostat queued nasa_10_f_bs for {sector} instead of answering; rerun later")
        parts.append(pd.read_csv(path, sep="\t", dtype=str))
    tsv = pd.concat(parts, ignore_index=True)
    tsv.columns = [c.strip() for c in tsv.columns]
    keys = tsv.columns[0]
    tsv[keys] = tsv[keys].str.split(",", n=1).str[1]  # drop the frequency
    tsv = tsv.rename(columns={keys: r"unit,co_nco,sector,finpos,na_item,geo\time"})
    for year in tsv.columns[1:]:
        tsv[year] = tsv[year].str.strip()
    tsv.to_csv(out / "eurostat" / "nasa_10_f_bs.csv", index=False)
    sources["eurostat/nasa_10_f_bs.csv"] = f"public, full: {url}"
    return sources


def house_prices(downloads: Path, out: Path) -> dict[str, str]:
    df = pd.read_csv(fetch(HOUSE_PRICES, downloads / "oecd" / "house_prices.csv"))
    old = pd.DataFrame(
        {
            "COU": df["REF_AREA"],
            "Country": df["Reference area"],
            "IND": df["MEASURE"],
            "Indicator": df["Measure"],
            "TIME": df["TIME_PERIOD"],
            "Value": df["OBS_VALUE"],
        }
    )
    old.to_csv(out / "oecd_econ" / "HOUSE_PRICES.csv", index=False)
    return {"oecd_econ/HOUSE_PRICES.csv": f"public, full (OECD.Stat layout, base year 2015): {HOUSE_PRICES}"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", type=Path, default=DATASETS)
    args = parser.parse_args()
    downloads, out = args.datasets / "downloads", args.datasets / "macro_raw_data"

    copy_sample(out)
    sources = {str(p.relative_to(out)): "sample copy" for p in sorted(out.rglob("*")) if p.is_file()}
    for directory in SPOOFED:
        for p in (out / directory).rglob("*"):
            if p.is_file():
                sources[str(p.relative_to(out))] = "SPOOFED sample copy: replace with the licensed micro-data (D1)"
    sources |= icio(downloads, out) | eurostat(downloads, out) | house_prices(downloads, out)
    sources = {k: sources[k] for k in sorted(sources)}
    (out / "SOURCES.json").write_text(json.dumps({"built": date.today().isoformat(), "files": sources}, indent=1))
    missing = [y for y in ICIO_YEARS if not (out / "icio" / f"{y}_SML.csv").exists()]
    print(f"{out}: {sum(v.startswith('public') for v in sources.values())} files replaced by full public data")
    print(f"ICIO years missing: {missing or 'none'}")


if __name__ == "__main__":
    main()
