using Model.Core.Results;
using Model.Core.Results.PerHour;

namespace Model.Core.Abstractions;

public interface IScenarioSimulator<THourResult, TRunSummary>
{
    SimulationResult<THourResult, TRunSummary> Run(
        IReadOnlyList<WeatherPoint> weather);
}
