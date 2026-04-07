using Model.Core.Results.PerHour;

namespace Model.Core.Components.Results;

public sealed record HybridDispatchResult(
    BatteryHourMetrics Battery,
    LoadCoverageMetrics Coverage,
    double FuelUsedL,
    double CurtailmentKWh);
    