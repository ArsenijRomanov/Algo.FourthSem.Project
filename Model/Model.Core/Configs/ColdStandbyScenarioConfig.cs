namespace Model.Core.Configs;

public sealed record ColdStandbyScenarioConfig(
    LoadConfig Load,
    DieselConfig PrimaryDiesel,
    DieselConfig ReserveDiesel);
    