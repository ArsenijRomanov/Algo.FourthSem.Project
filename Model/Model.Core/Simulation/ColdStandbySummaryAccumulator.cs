using Model.Core.Results.FullRun;
using Model.Core.Results.PerHour;

namespace Model.Core.Simulation;

public sealed class ColdStandbySummaryAccumulator
{
    private const double Epsilon = 1e-9;

    private int _hours;
    private double _totalLoadKWh;
    private double _totalDieselEnergyKWh;
    private double _dieselToLoadKWh;
    private double _fuelUsedL;

    private double _primaryRunHours;
    private double _reserveRunHours;

    private int _primaryFailureCount;
    private int _reserveFailureCount;
    private int _primaryRecoveryCount;
    private int _reserveRecoveryCount;

    private double _primaryRepairHours;
    private double _reserveRepairHours;

    private double _systemDownHours;
    private double _unservedEnergyKWh;
    private double _hoursLoadFullyCovered;

    public void Add(ColdStandbyHourResult hour)
    {
        ArgumentNullException.ThrowIfNull(hour);

        _hours++;

        var loadKWh =
            hour.Coverage.CoveredByDieselKWh +
            hour.Coverage.UnservedEnergyKWh;

        _totalLoadKWh += loadKWh;
        _totalDieselEnergyKWh += hour.Coverage.CoveredByDieselKWh;
        _dieselToLoadKWh += hour.Coverage.CoveredByDieselKWh;

        _fuelUsedL += hour.Primary.FuelUsedL + hour.Reserve.FuelUsedL;

        if (hour.Primary.FuelUsedL > Epsilon)
            _primaryRunHours += 1.0;

        if (hour.Reserve.FuelUsedL > Epsilon)
            _reserveRunHours += 1.0;

        if (hour.Primary.FailedThisHour)
            _primaryFailureCount++;

        if (hour.Reserve.FailedThisHour)
            _reserveFailureCount++;

        if (hour.Primary.RecoveredThisHour)
            _primaryRecoveryCount++;

        if (hour.Reserve.RecoveredThisHour)
            _reserveRecoveryCount++;

        if (!hour.Primary.IsAvailable)
            _primaryRepairHours += 1.0;

        if (!hour.Reserve.IsAvailable)
            _reserveRepairHours += 1.0;

        if (hour.Coverage.UnservedEnergyKWh > Epsilon)
            _systemDownHours += 1.0;
        else
            _hoursLoadFullyCovered += 1.0;

        _unservedEnergyKWh += hour.Coverage.UnservedEnergyKWh;
    }

    public ColdStandbyRunSummary Build()
    {
        var availability = _hours == 0
            ? 1.0
            : _hoursLoadFullyCovered / _hours;

        return new ColdStandbyRunSummary(
            TotalLoadKWh: _totalLoadKWh,
            TotalDieselEnergyKWh: _totalDieselEnergyKWh,
            DieselToLoadKWh: _dieselToLoadKWh,
            FuelUsedL: _fuelUsedL,

            PrimaryRunHours: _primaryRunHours,
            ReserveRunHours: _reserveRunHours,

            PrimaryFailureCount: _primaryFailureCount,
            ReserveFailureCount: _reserveFailureCount,
            PrimaryRecoveryCount: _primaryRecoveryCount,
            ReserveRecoveryCount: _reserveRecoveryCount,

            PrimaryRepairHours: _primaryRepairHours,
            ReserveRepairHours: _reserveRepairHours,

            SystemDownHours: _systemDownHours,
            UnservedEnergyKWh: _unservedEnergyKWh,
            HoursLoadFullyCovered: _hoursLoadFullyCovered,
            Availability: availability);
    }
}
