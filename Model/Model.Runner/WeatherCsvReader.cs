using System.Globalization;
using Model.Core;

namespace Model.Runner;

public static class WeatherCsvReader
{
    public static IReadOnlyList<WeatherPoint> Read(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
            throw new ArgumentException("CSV path is empty.", nameof(path));

        if (!File.Exists(path))
            throw new FileNotFoundException("Weather CSV file not found.", path);

        var lines = File.ReadAllLines(path);
        if (lines.Length < 2)
            throw new InvalidOperationException("Weather CSV is empty.");

        var header = lines[0].Split(',');
        var index = BuildColumnIndex(header);

        var result = new List<WeatherPoint>(lines.Length - 1);

        for (var i = 1; i < lines.Length; i++)
        {
            var line = lines[i];
            if (string.IsNullOrWhiteSpace(line))
                continue;

            var parts = line.Split(',');
            if (parts.Length < header.Length)
                throw new InvalidOperationException($"Invalid CSV row at line {i + 1}.");

            var timestamp = DateTime.Parse(parts[index["datetime_msk"]], CultureInfo.InvariantCulture);
            var gti = double.Parse(parts[index["GTI_W_m2"]], CultureInfo.InvariantCulture);
            var tAir = double.Parse(parts[index["temp_C"]], CultureInfo.InvariantCulture);
            var wind = double.Parse(parts[index["wind_m_s"]], CultureInfo.InvariantCulture);

            result.Add(new WeatherPoint(
                TimestampMsk: timestamp,
                GtiWm2: gti,
                TAirC: tAir,
                WindMs: wind));
        }

        return result;
    }

    private static Dictionary<string, int> BuildColumnIndex(string[] header)
    {
        var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        for (var i = 0; i < header.Length; i++)
            map[header[i].Trim()] = i;

        Require(map, "datetime_msk");
        Require(map, "GTI_W_m2");
        Require(map, "temp_C");
        Require(map, "wind_m_s");

        return map;
    }

    private static void Require(Dictionary<string, int> map, string columnName)
    {
        if (!map.ContainsKey(columnName))
            throw new InvalidOperationException($"CSV column '{columnName}' not found.");
    }
}