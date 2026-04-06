using Model.Core.Configs;
using Model.Core.Results.FullRun;
using Model.Core.Results.PerHour;

namespace Model.Core.Abstractions;

public interface IHybridSystemSimulator
    : IScenarioSimulator<HybridScenarioConfig, HybridHourResult, HybridRunSummary>
{
}
