using Model.Core.Results;
using Model.Core.Results.PerHour;

namespace Model.Core.Abstractions;

public interface IScenarioSimulator<in TConfig, THourResult, TRunSummary>
{
    SimulationResult<THourResult, TRunSummary> Run(
        IReadOnlyList<WeatherPoint> weather,
        TConfig config);
}
