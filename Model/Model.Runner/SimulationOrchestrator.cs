using Model.Core;
using Model.Core.Components;
using Model.Core.Configs;
using Model.Core.Results.FullRun;
using Model.Core.Simulation;

namespace Model.Runner;

public sealed class SimulationOrchestrator
{
    public void Run(AppConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);

        var weather = WeatherCsvReader.Read(config.WeatherCsvPath);

        if (config.SingleRun)
        {
            RunSingle(config, weather);
            return;
        }

        RunMonteCarlo(config, weather);
    }

    private void RunSingle(AppConfig config, IReadOnlyList<WeatherPoint> weather)
    {
        var seed = config.SingleRunSeed;

        switch (config.ScenarioType)
        {
            case ScenarioType.Hybrid:
            {
                var simulator = new HybridSystemSimulator(
                    config.Hybrid,
                    new SystemRandomSource(seed));

                var result = simulator.Run(weather);

                ResultWriter.WriteHybridSingleRun(
                    config.OutputDirectory,
                    seed,
                    result.Summary,
                    result.Hours);

                break;
            }

            case ScenarioType.ColdStandby:
            {
                var simulator = new ColdStandbyDieselSimulator(
                    config.ColdStandby,
                    new SystemRandomSource(seed));

                var result = simulator.Run(weather);

                ResultWriter.WriteColdStandbySingleRun(
                    config.OutputDirectory,
                    seed,
                    result.Summary,
                    result.Hours);

                break;
            }

            default:
                throw new InvalidOperationException($"Unsupported scenario type: {config.ScenarioType}");
        }
    }

    private void RunMonteCarlo(AppConfig config, IReadOnlyList<WeatherPoint> weather)
    {
        switch (config.ScenarioType)
        {
            case ScenarioType.Hybrid:
            {
                var summaries = new List<HybridRunSummary>(config.RunCount);

                for (var seed = 1; seed <= config.RunCount; seed++)
                {
                    var simulator = new HybridSystemSimulator(
                        config.Hybrid,
                        new SystemRandomSource(seed));

                    var result = simulator.Run(weather);
                    summaries.Add(result.Summary);
                }

                ResultWriter.WriteHybridMonteCarlo(
                    config.OutputDirectory,
                    summaries);

                break;
            }

            case ScenarioType.ColdStandby:
            {
                var summaries = new List<ColdStandbyRunSummary>(config.RunCount);

                for (var seed = 1; seed <= config.RunCount; seed++)
                {
                    var simulator = new ColdStandbyDieselSimulator(
                        config.ColdStandby,
                        new SystemRandomSource(seed));

                    var result = simulator.Run(weather);
                    summaries.Add(result.Summary);
                }

                ResultWriter.WriteColdStandbyMonteCarlo(
                    config.OutputDirectory,
                    summaries);

                break;
            }

            default:
                throw new InvalidOperationException($"Unsupported scenario type: {config.ScenarioType}");
        }
    }
}