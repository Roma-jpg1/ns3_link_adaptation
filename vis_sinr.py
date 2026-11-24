import argparse
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt


parser = argparse.ArgumentParser(description="Графики SINR, MCS и BLER из результатов ns-3.")
parser.add_argument("folder", nargs="?", type=Path, default=Path(__file__).resolve().parent,
                    help="Папка с файлами статистики и run.log")
parser.add_argument("--output", type=Path, help="Сохранить график в указанный файл")
parser.add_argument("--no-show", action="store_true", help="Сохранить график без открытия окна")
parser.add_argument("--up-threshold", type=float, help="Порог повышения MCS, например 0.07")
parser.add_argument("--down-threshold", type=float, help="Порог снижения MCS, например 0.12")
args = parser.parse_args()
folder = args.folder.resolve()

for threshold in (args.up_threshold, args.down_threshold):
    if threshold is not None and not 0 <= threshold <= 1:
        parser.error("Пороги BLER должны находиться в диапазоне от 0 до 1")
if (args.up_threshold is not None and args.down_threshold is not None
        and args.up_threshold >= args.down_threshold):
    parser.error("Порог повышения MCS должен быть меньше порога снижения")


def read_table(file_name):
    rows = []
    with open(folder / file_name, encoding="utf-8") as file:
        columns = []
        for line in file:
            line = line.strip()
            if not line:
                continue
            if line.startswith("%"):
                columns = line[1:].split()
            elif columns:
                values = line.split()
                if len(values) >= len(columns):
                    rows.append(dict(zip(columns, values)))
    return rows


def group_by_ue(rows):
    groups = {}
    for row in rows:
        cell = row.get("cellId", row.get("CellId"))
        name = f"Сота {cell}, UE {row['IMSI']}"
        if name not in groups:
            groups[name] = []
        groups[name].append(row)
    return groups


def read_interference(file_name):
    # В этом файле значения и время следующей записи могут быть склеены.
    text = (folder / file_name).read_text(encoding="utf-8").split("\n", 1)[-1]
    pattern = r"(?:\A|(?<=\s)|(?<=[eE][+-]\d\d))(?P<time>\d+(?:\.\d+)?)\t(?P<cell>\d+)\t"
    starts = list(re.finditer(pattern, text))
    rows = []

    for i, start in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        values = [float(value) for value in text[start.end():end].split()]
        if values:
            rows.append({
                "time": float(start.group("time")),
                "cell": start.group("cell"),
                "interference": sum(values) / len(values),
            })
    return rows


def read_adaptation_log():
    decisions = []
    windows = []
    log_path = folder / "run.log"
    if not log_path.exists():
        return decisions, windows

    timestamp = r"\+(?P<time>\d+(?:\.\d+)?)s.*?"
    mcs_pattern = re.compile(
        timestamp + r"SIMPLE_MCS cqi=(?P<cqi>\d+) base=(?P<base>\d+) "
        r"selected=(?P<selected>\d+)"
    )
    bler_pattern = re.compile(
        timestamp + r"SIMPLE_BLER samples=(?P<samples>\d+) errors=(?P<errors>\d+) "
        r"bler=(?P<bler>[\d.eE+-]+)"
    )

    with log_path.open(encoding="utf-8", errors="replace") as file:
        for line in file:
            if "SIMPLE_MCS" in line:
                match = mcs_pattern.search(line)
                if match:
                    decisions.append({
                        "time": float(match["time"]),
                        "base": int(match["base"]),
                    })
            elif "SIMPLE_BLER" in line:
                match = bler_pattern.search(line)
                if match:
                    windows.append({
                        "time": float(match["time"]),
                        "samples": int(match["samples"]),
                        "bler": float(match["bler"]),
                    })
    return decisions, windows


files = [
    "DlMacStats.txt", "DlRsrpSinrStats.txt",
    "UlMacStats.txt", "UlSinrStats.txt",
]

tables = {}
for file_name in files:
    tables[file_name] = read_table(file_name)
    if not tables[file_name]:
        raise SystemExit(f"В файле нет данных: {file_name}")

interference = read_interference("UlInterferenceStats.txt")
if not interference:
    raise SystemExit("В файле UlInterferenceStats.txt нет данных")

decisions, windows = read_adaptation_log()
if windows:
    fig, axes = plt.subplots(4, 1, figsize=(12, 13), sharex=True)
    sinr_axis, mcs_axis, bler_axis, interference_axis = axes
else:
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    sinr_axis, mcs_axis, interference_axis = axes

# SINR переводим из линейных значений в децибелы.
for file_name, direction, column in [
    ("DlRsrpSinrStats.txt", "DL", "sinr"),
    ("UlSinrStats.txt", "UL", "sinrLinear"),
]:
    for ue, rows in group_by_ue(tables[file_name]).items():
        rows.sort(key=lambda row: float(row["time"]))
        times = []
        values = []
        for row in rows:
            sinr = float(row[column])
            if sinr > 0:
                times.append(float(row["time"]))
                values.append(10 * math.log10(sinr))
        sinr_axis.plot(times, values, label=f"{ue}, {direction}")

sinr_axis.set_title("SINR DL и UL")
sinr_axis.set_ylabel("дБ")

# Назначения MCS на уровне MAC.
for file_name, direction, column in [
    ("DlMacStats.txt", "DL", "mcsTb1"),
    ("UlMacStats.txt", "UL", "mcs"),
]:
    for ue, rows in group_by_ue(tables[file_name]).items():
        rows.sort(key=lambda row: float(row["time"]))
        times = [float(row["time"]) for row in rows]
        values = [int(row[column]) for row in rows]
        mcs_axis.step(times, values, where="post", label=f"{ue}, {direction}: выбранный MCS")

if decisions:
    mcs_axis.step(
        [row["time"] for row in decisions],
        [row["base"] for row in decisions],
        where="post", linestyle="--", color="black", alpha=0.7,
        label="DL: базовый MCS по CQI",
    )

mcs_axis.set_title("MCS DL и UL")
mcs_axis.set_ylabel("MCS")

if windows:
    bler_axis.step(
        [row["time"] for row in windows],
        [100 * row["bler"] for row in windows],
        where="post", color="tab:red", label="BLER первых попыток передачи",
    )
    for threshold, color, label in [
        (args.up_threshold, "tab:green", "Порог повышения MCS"),
        (args.down_threshold, "tab:orange", "Порог снижения MCS"),
    ]:
        if threshold is not None:
            bler_axis.axhline(100 * threshold, color=color, linestyle="--",
                              label=f"{label}: {100 * threshold:g}%")
    bler_axis.set_title(f"BLER DL: окно из {windows[0]['samples']} первых передач")
    bler_axis.set_ylabel("Ошибки, %")
    bler_axis.set_ylim(0, 100)

# Средняя спектральная плотность помех по ресурсным блокам.
cells = {}
for row in interference:
    cell = row["cell"]
    if cell not in cells:
        cells[cell] = []
    cells[cell].append(row)

for cell, rows in cells.items():
    rows.sort(key=lambda row: row["time"])
    times = []
    values = []
    for row in rows:
        if row["interference"] > 0:
            times.append(row["time"])
            values.append(10 * math.log10(row["interference"]))
    interference_axis.plot(times, values, marker=".", label=f"Сота {cell}")

interference_axis.set_title("Помехи и шум UL")
interference_axis.set_ylabel("дБВт/Гц")

for axis in axes.flat:
    axis.set_xlabel("Время, с")
    axis.grid()
    axis.legend(fontsize="small")

plt.tight_layout()
output = args.output
if args.no_show and output is None:
    output = folder / "sinr_mcs_bler.png"
if output is not None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160)
    print(f"График сохранён: {output}")
print(f"Данные: {folder}")
print(f"Решений MCS в логе: {len(decisions)}; окон BLER: {len(windows)}")
if args.no_show:
    plt.close(fig)
else:
    plt.show()
