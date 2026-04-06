namespace Model.Core.Results.FullRun;

public sealed record HybridRunSummary(
    double TotalLoadKWh,
    double TotalPvGenerationKWh,
    double TotalBatteryChargeKWh,
    double TotalBatteryDischargeKWh,
    double TotalDieselEnergyKWh,

    double PvToLoadKWh,
    double BatteryToLoadKWh,
    double DieselToLoadKWh,

    double DieselRunHours,
    double FuelUsedL,
    int FailureCount,
    int RecoveryCount,
    double TotalRepairHours,

    double SystemDownHours,
    double UnservedEnergyKWh,
    double HoursLoadFullyCovered,
    double Availability,

    double SocMinKWh,
    double SocMaxKWh,
    double SocAverageKWh,
    double HoursBatteryCharging,
    double HoursBatteryDischarging,

    double CurtailmentKWh);
    