namespace Model.Core.Results.FullRun;

public sealed record ColdStandbyRunSummary(
    double TotalLoadKWh,
    double TotalDieselEnergyKWh,
    double DieselToLoadKWh,
    double FuelUsedL,

    double PrimaryRunHours,
    double ReserveRunHours,

    int PrimaryFailureCount,
    int ReserveFailureCount,
    int PrimaryRecoveryCount,
    int ReserveRecoveryCount,

    double PrimaryRepairHours,
    double ReserveRepairHours,

    double SystemDownHours,
    double UnservedEnergyKWh,
    double HoursLoadFullyCovered,
    double Availability);
    