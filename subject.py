#!/usr/bin/env python3.8

from pprint import pp
import sys
from pathlib import Path
from dataclasses import dataclass
import dataclasses
import re
import csv
import typing

OUT_DIR_REGEX = re.compile(r"^out-([a-z-]+)-([a-z]+-[0-9]+)-([0-9]+)$")


@dataclass
# Coverage metrics at a single point in time
class CovMetrics:
    time: int
    l_per: float
    l_abs: int
    b_per: float
    b_abs: int


@dataclass
class Result:
    dir: Path
    subject: str
    fuzzer: str
    run_no: int
    final_cov_data: CovMetrics
    fuzzer_stats: dict


@dataclass
class TableRow:
    fuzzer: str
    run_no: int
    time_spent: int
    total_execs: int
    ave_execs_per_sec: int
    b_cov_percent: float
    l_cov_percent: float


def canonicalize(v: str):
    try:
        return int(v)
    except ValueError:
        return v


def extract_fuzzer_stats(s: str) -> dict:
    d = dict()
    for l in s.splitlines():
        l = l.strip()
        if not l:
            continue
        [k, v] = l.split(":", maxsplit=1)
        k = k.strip()
        v = v.strip()
        assert k not in d
        d[k] = canonicalize(v)
    return d


def uniq(l):
    r = []
    for i in l:
        if i not in r:
            r.append(i)
    return r


def extract_dir(path: Path) -> Result:
    print(f"Extracting {path}")
    m = OUT_DIR_REGEX.match(path.name)
    if m is None:
        raise ValueError(f"invalid path {path.name}")
    subject, fuzzzer, run_no = m.group(1, 2, 3)

    with open(path / "cov_over_time.csv") as f:
        lines = list(csv.reader(f))
        assert lines[0] == ["Time", "l_per", "l_abs", "b_per", "b_abs"]
        [time, l_per, l_abs, b_per, b_abs] = lines[-1]
        final_cov_data = CovMetrics(
            time, float(l_per), int(l_abs), float(b_per), int(b_abs)
        )

    with open(path / "fuzzer_stats") as f:
        fuzzer_stats = extract_fuzzer_stats(f.read())

    return Result(path, subject, fuzzzer, run_no, final_cov_data, fuzzer_stats)


def make_table_row(stats: Result) -> TableRow:

    fuzzer = stats.fuzzer
    run_no = stats.run_no

    time_spent = stats.fuzzer_stats["last_update"] - stats.fuzzer_stats["start_time"]
    total_execs = stats.fuzzer_stats["execs_done"]
    ave_execs_per_sec = total_execs / time_spent

    b_cov_percent = stats.final_cov_data.b_per
    l_cov_percent = stats.final_cov_data.l_per

    return TableRow(
        fuzzer,
        run_no,
        time_spent,
        total_execs,
        ave_execs_per_sec,
        b_cov_percent,
        l_cov_percent,
    )


def ave(x):
    return sum(x) / len(x)


def argigate_rows(rows: typing.List[TableRow]) -> TableRow:
    # TODO: Just use pandas
    fuzzers = [x.fuzzer for x in rows]
    run_nos = [x.run_no for x in rows]
    time_spents = [x.time_spent for x in rows]
    total_execss = [x.total_execs for x in rows]
    ave_execs_per_secs = [x.ave_execs_per_sec for x in rows]
    b_cov_percents = [x.b_cov_percent for x in rows]
    l_cov_percents = [x.l_cov_percent for x in rows]

    assert len(set(fuzzers)) == 1, f"Duplucate fuzzers in {fuzzers}"
    assert len(set(run_nos)) == len(rows)

    return TableRow(
        fuzzer=fuzzers[0],
        run_no="average",
        time_spent=ave(time_spents),
        total_execs=ave(total_execss),
        ave_execs_per_sec=ave(ave_execs_per_secs),
        b_cov_percent=ave(b_cov_percents),
        l_cov_percent=ave(l_cov_percents),
    )


def write_all(f, data):
    # Based on https://github.com/dfurtado/dataclass-csv/blob/master/dataclass_csv/dataclass_writer.py
    assert isinstance(data, list)
    cls = type(data[0])
    fieldnames = [x.name for x in dataclasses.fields(cls)]
    w = csv.writer(f)

    w.writerow(fieldnames)

    for d in data:
        assert isinstance(d, cls)
        row = dataclasses.astuple(d)
        w.writerow(row)


def main(dir):
    if not isinstance(dir, Path):
        dir = Path(dir)

    print(f"analysing {dir}")
    out_folders = [x for x in dir.glob("out-*-*-*") if x.is_dir()]

    rows: typing.List[TableRow] = []

    for f in out_folders:
        rows.append(make_table_row(extract_dir(f)))

    rows.sort(key=lambda x: x.run_no)
    rows.sort(key=lambda x: x.fuzzer)

    fuzzers = uniq([r.fuzzer for r in rows])

    agg_rows = []

    for fuzzer in fuzzers:
        these_rows = [r for r in rows if r.fuzzer == fuzzer]
        agg_rows.append(argigate_rows(these_rows))

    rows.extend(agg_rows)

    with open("data.csv", "w") as f:
        write_all(f, rows)


if __name__ == "__main__":
    [_, dir] = sys.argv
    main(dir)
