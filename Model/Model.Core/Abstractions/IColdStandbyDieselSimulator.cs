using Model.Core.Configs;
using Model.Core.Results.FullRun;
using Model.Core.Results.PerHour;

namespace Model.Core.Abstractions;

public interface IColdStandbyDieselSimulator
    : IScenarioSimulator<ColdStandbyScenarioConfig, ColdStandbyHourResult, ColdStandbyRunSummary>
{
}
