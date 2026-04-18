# python reduce_gti.py weather_msk.csv

import argparse
from pathlib import Path

import pandas as pd

# Коэффициент масштабирования GTI
GTI_SCALE = 0.4

# Название столбца с GTI
GTI_COLUMN = "GTI_W_m2"


def format_scale_for_filename(scale: float) -> str:
    """
    Преобразует коэффициент в безопасный вид для имени файла.
    Например:
    0.7  -> 0_7
    1.0  -> 1_0
    0.85 -> 0_85
    """
    return str(scale).replace(".", "_")


def build_output_path(input_path: Path, scale: float) -> Path:
    """
    Формирует имя выходного файла на основе входного.
    Например:
    weather_msk.csv -> weather_msk_gti_x0_7.csv
    """
    scale_str = format_scale_for_filename(scale)
    return input_path.with_name(f"{input_path.stem}_gti_x{scale_str}{input_path.suffix}")


def scale_gti(input_file: str) -> Path:
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Файл не найден: {input_path}")

    df = pd.read_csv(input_path)

    if GTI_COLUMN not in df.columns:
        raise ValueError(f"В файле нет столбца '{GTI_COLUMN}'")

    df[GTI_COLUMN] = df[GTI_COLUMN] * GTI_SCALE

    output_path = build_output_path(input_path, GTI_SCALE)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Умножить столбец GTI_W_m2 на коэффициент и сохранить новый CSV."
    )
    parser.add_argument("input_file", help="Путь к исходному CSV-файлу")

    args = parser.parse_args()

    try:
        output_path = scale_gti(args.input_file)
        print(f"Готово: {output_path}")
        print(f"{GTI_COLUMN} умножен на коэффициент {GTI_SCALE}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
