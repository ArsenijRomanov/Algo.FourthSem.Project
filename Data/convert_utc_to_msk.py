# python convert_utc_to_msk.py <откуда> <куда>

import argparse
import sys
from pathlib import Path

import pandas as pd


def convert_utc_to_msk(input_file: str, output_file: str) -> None:
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Файл не найден: {input_path}")

    df = pd.read_csv(input_path)

    source_column = "datetime_utc"
    target_column = "datetime_msk"

    if source_column not in df.columns:
        raise ValueError(f"В файле нет столбца '{source_column}'")

    # Парсим UTC-время, прибавляем 3 часа и заменяем исходный столбец
    dt = pd.to_datetime(df[source_column], format="%Y-%m-%d %H:%M:%S", errors="raise")
    dt_msk = dt + pd.Timedelta(hours=3)

    df[source_column] = dt_msk.dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.rename(columns={source_column: target_column})

    df.to_csv(output_path, index=False)
    print(f"Готово: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Конвертировать столбец datetime_utc из UTC в МСК (UTC+3), переименовать его в datetime_msk и сохранить новый CSV."
    )
    parser.add_argument("input_file", help="Путь к исходному CSV-файлу")
    parser.add_argument("output_file", help="Путь к новому CSV-файлу")

    args = parser.parse_args()

    try:
        convert_utc_to_msk(args.input_file, args.output_file)
        return 0
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())