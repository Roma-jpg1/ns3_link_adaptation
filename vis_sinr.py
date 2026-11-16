import math
import re
from pathlib import Path

import matplotlib.pyplot as plt


folder = Path(__file__).resolve().parent


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

fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
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
        mcs_axis.step(times, values, where="post", marker="o", label=f"{ue}, {direction}")

mcs_axis.set_title("MCS DL и UL")
mcs_axis.set_ylabel("MCS")

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
plt.show()
