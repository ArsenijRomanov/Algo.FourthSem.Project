namespace Model.Core.States.Battery;

public sealed record BatteryDischargeResult(
    double LoadRequestedKWh,
    double EnergyDeliveredToLoadKWh,
    double EnergyWithdrawnFromSocKWh,
    double UncoveredLoadKWh,
    double SocEndKWh);