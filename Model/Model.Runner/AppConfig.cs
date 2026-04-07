using System.Text.Json;
using System.Text.Json.Serialization;
using Model.Core.Configs;

namespace Model.Runner;

public sealed record AppConfig(
    ScenarioType ScenarioType,
    bool SingleRun,
    int SingleRunSeed,
    int RunCount,
    string WeatherCsvPath,
    string OutputDirectory,
    HybridScenarioConfig Hybrid,
    ColdStandbyScenarioConfig ColdStandby)
{
    public static AppConfig Load(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
            throw new ArgumentException("Config path is empty.", nameof(path));

        if (!File.Exists(path))
            throw new FileNotFoundException("Config file not found.", path);

        var json = File.ReadAllText(path);

        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };
        options.Converters.Add(new JsonStringEnumConverter());

        var config = JsonSerializer.Deserialize<AppConfig>(json, options)
                     ?? throw new InvalidOperationException("Failed to parse config.");

        Validate(config);
        return config;
    }

    private static void Validate(AppConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.WeatherCsvPath))
            throw new InvalidOperationException("WeatherCsvPath is required.");

        if (string.IsNullOrWhiteSpace(config.OutputDirectory))
            throw new InvalidOperationException("OutputDirectory is required.");

        if (config.SingleRun)
        {
            if (config.SingleRunSeed <= 0)
                throw new InvalidOperationException("SingleRunSeed must be > 0 when SingleRun = true.");
        }
        else
        {
            if (config.RunCount <= 0)
                throw new InvalidOperationException("RunCount must be > 0 when SingleRun = false.");
        }
    }
}