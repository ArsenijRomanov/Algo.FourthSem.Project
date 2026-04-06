namespace Model.Core.Configs;

public sealed record HybridScenarioConfig(
    LoadConfig Load,
    PvSystemConfig Pv,
    BatteryConfig Battery,
    DieselConfig Diesel);
    