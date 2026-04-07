namespace Model.Core.States.Battery;

public sealed record BatteryChargeResult(
    double EnergyOfferedKWh,
    double EnergyAcceptedKWh,
    double EnergyStoredInSocKWh,
    double EnergyRejectedKWh,
    double SocEndKWh);
    