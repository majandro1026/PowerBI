import argparse
import csv
import os
import re
from datetime import datetime

SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

WEEKDAY_PREFIX = re.compile(r"^[A-Za-záéíóúñÁÉÍÓÚÑ]+,\s*")
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
SLASH_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$")
SPANISH_DATE_RE = re.compile(
    r"^(?:[A-Za-záéíóúñÁÉÍÓÚÑ]+,\s*)?(\d{1,2})\s+de\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+)\s+de\s+(\d{4})$",
    re.IGNORECASE,
)


def parse_date_value(value: str) -> str:
    if value is None:
        return ""

    raw = value.strip().strip('"').strip("'")
    if not raw:
        return ""

    iso_match = ISO_DATE_RE.match(raw)
    if iso_match:
        year, month, day = iso_match.groups()
        return f"{int(day):02d}/{int(month):02d}/{int(year):04d}"

    slash_match = SLASH_DATE_RE.match(raw)
    if slash_match:
        day, month, year = slash_match.groups()
        year = int(year)
        if year < 100:
            year += 2000 if year < 70 else 1900
        return f"{int(day):02d}/{int(month):02d}/{year:04d}"

    raw = WEEKDAY_PREFIX.sub("", raw)
    spanish_match = SPANISH_DATE_RE.match(raw)
    if spanish_match:
        day, month_name, year = spanish_match.groups()
        month = SPANISH_MONTHS.get(month_name.lower())
        if month:
            return f"{int(day):02d}/{month:02d}/{int(year):04d}"

    # Attempt generic parse with datetime, preserving if it fails
    for fmt in ["%d %B %Y", "%d %b %Y", "%Y%m%d", "%d-%m-%Y", "%Y/%m/%d"]:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue

    return raw


def transform_csv_file(file_path: str) -> int:
    updated_count = 0
    with open(file_path, mode="r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        fieldnames = reader.fieldnames
        if not fieldnames:
            return 0

        if "Fecha Inicio" not in fieldnames and "Fecha Fin" not in fieldnames:
            return 0

        rows = []
        for row in reader:
            for column in ["Fecha Inicio", "Fecha Fin"]:
                if column in row:
                    original = row[column]
                    normalized = parse_date_value(original)
                    if normalized != original:
                        updated_count += 1
                        row[column] = normalized
            rows.append(row)

    if updated_count == 0:
        return 0

    temp_path = file_path + ".tmp"
    with open(temp_path, mode="w", encoding="utf-8", newline="") as target_file:
        writer = csv.DictWriter(target_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    os.replace(temp_path, file_path)
    return updated_count


def find_csv_files(root: str):
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(".csv"):
                yield os.path.join(dirpath, name)


def main():
    parser = argparse.ArgumentParser(
        description="Transform Fecha Inicio and Fecha Fin values in all CSV files to dd/mm/yyyy format."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=os.getcwd(),
        help="Workspace root path to search for CSV files (default: current directory).",
    )
    args = parser.parse_args()

    root_path = os.path.abspath(args.root)
    total_files = 0
    total_updates = 0

    for csv_file in find_csv_files(root_path):
        result = transform_csv_file(csv_file)
        if result is not None:
            total_files += 1
            total_updates += result
            if result > 0:
                print(f"Updated {result} date values in: {csv_file}")

    print(f"Processed {total_files} CSV files in '{root_path}'.")
    print(f"Total date values updated: {total_updates}")


if __name__ == "__main__":
    main()
