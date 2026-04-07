using Model.Core.Results.FullRun;
using Model.Core.Results.PerHour;

namespace Model.Core.Simulation;

public sealed class HybridSummaryAccumulator
{
    private const double Epsilon = 1e-9;

    private int _hours;
    private double _totalLoadKWh;
    private double _totalPvGenerationKWh;
    private double _totalBatteryChargeKWh;
    private double _totalBatteryDischargeKWh;
    private double _totalDieselEnergyKWh;

    private double _pvToLoadKWh;
    private double _batteryToLoadKWh;
    private double _dieselToLoadKWh;

    private double _dieselRunHours;
    private double _fuelUsedL;
    private int _failureCount;
    private int _recoveryCount;
    private double _totalRepairHours;

    private double _systemDownHours;
    private double _unservedEnergyKWh;
    private double _hoursLoadFullyCovered;

    private double _socMinKWh = double.MaxValue;
    private double _socMaxKWh = double.MinValue;
    private double _socSumKWh;
    private double _hoursBatteryCharging;
    private double _hoursBatteryDischarging;

    private double _curtailmentKWh;

    public void Add(HybridHourResult hour, double curtailmentKWh)
    {
        ArgumentNullException.ThrowIfNull(hour);

        _hours++;

        var loadKWh =
            hour.Coverage.CoveredByPvKWh +
            hour.Coverage.CoveredByBatteryKWh +
            hour.Coverage.CoveredByDieselKWh +
            hour.Coverage.UnservedEnergyKWh;

        _totalLoadKWh += loadKWh;
        _totalPvGenerationKWh += hour.Pv.EPvKWh;
        _totalBatteryChargeKWh += hour.Battery.ChargeKWh;
        _totalBatteryDischargeKWh += hour.Battery.DischargeKWh;
        _totalDieselEnergyKWh += hour.Coverage.CoveredByDieselKWh;

        _pvToLoadKWh += hour.Coverage.CoveredByPvKWh;
        _batteryToLoadKWh += hour.Coverage.CoveredByBatteryKWh;
        _dieselToLoadKWh += hour.Coverage.CoveredByDieselKWh;

        if (hour.Coverage.CoveredByDieselKWh > Epsilon)
            _dieselRunHours += 1.0;

        _fuelUsedL += hour.Diesel.FuelUsedL;

        if (hour.Diesel.FailedThisHour)
            _failureCount++;

        if (hour.Diesel.RecoveredThisHour)
            _recoveryCount++;

        if (!hour.Diesel.IsAvailable)
            _totalRepairHours += 1.0;

        if (hour.Coverage.UnservedEnergyKWh > Epsilon)
            _systemDownHours += 1.0;
        else
            _hoursLoadFullyCovered += 1.0;

        _unservedEnergyKWh += hour.Coverage.UnservedEnergyKWh;

        _socMinKWh = Math.Min(_socMinKWh, hour.Battery.SocKWh);
        _socMaxKWh = Math.Max(_socMaxKWh, hour.Battery.SocKWh);
        _socSumKWh += hour.Battery.SocKWh;

        if (hour.Battery.ChargeKWh > Epsilon)
            _hoursBatteryCharging += 1.0;

        if (hour.Battery.DischargeKWh > Epsilon)
            _hoursBatteryDischarging += 1.0;

        _curtailmentKWh += curtailmentKWh;
    }

    public HybridRunSummary Build()
    {
        var availability = _hours == 0
            ? 1.0
            : _hoursLoadFullyCovered / _hours;

        var socAverage = _hours == 0
            ? 0.0
            : _socSumKWh / _hours;

        var socMin = _hours == 0 ? 0.0 : _socMinKWh;
        var socMax = _hours == 0 ? 0.0 : _socMaxKWh;

        return new HybridRunSummary(
            TotalLoadKWh: _totalLoadKWh,
            TotalPvGenerationKWh: _totalPvGenerationKWh,
            TotalBatteryChargeKWh: _totalBatteryChargeKWh,
            TotalBatteryDischargeKWh: _totalBatteryDischargeKWh,
            TotalDieselEnergyKWh: _totalDieselEnergyKWh,

            PvToLoadKWh: _pvToLoadKWh,
            BatteryToLoadKWh: _batteryToLoadKWh,
            DieselToLoadKWh: _dieselToLoadKWh,

            DieselRunHours: _dieselRunHours,
            FuelUsedL: _fuelUsedL,
            FailureCount: _failureCount,
            RecoveryCount: _recoveryCount,
            TotalRepairHours: _totalRepairHours,

            SystemDownHours: _systemDownHours,
            UnservedEnergyKWh: _unservedEnergyKWh,
            HoursLoadFullyCovered: _hoursLoadFullyCovered,
            Availability: availability,

            SocMinKWh: socMin,
            SocMaxKWh: socMax,
            SocAverageKWh: socAverage,
            HoursBatteryCharging: _hoursBatteryCharging,
            HoursBatteryDischarging: _hoursBatteryDischarging,

            CurtailmentKWh: _curtailmentKWh);
    }
}
