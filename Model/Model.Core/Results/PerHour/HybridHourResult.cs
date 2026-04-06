namespace Model.Core.Results.PerHour;

public sealed record HybridHourResult(
    DateTime TimestampMsk,
    PvHourMetrics Pv,
    BatteryHourMetrics Battery,
    DieselHourMetrics Diesel,
    LoadCoverageMetrics Coverage);
    