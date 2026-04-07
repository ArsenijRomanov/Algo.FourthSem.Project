using Model.Core.Components.Results;
using Model.Core.Configs;
using Model.Core.Results.PerHour;
using Model.Core.States.Battery;

namespace Model.Core.Components;

public sealed class HybridDispatcher
{
    private readonly LoadConfig _loadConfig;
    private readonly DieselConfig _dieselConfig;

    public HybridDispatcher(
        LoadConfig loadConfig,
        DieselConfig dieselConfig)
    {
        _loadConfig = loadConfig ?? throw new ArgumentNullException(nameof(loadConfig));
        _dieselConfig = dieselConfig ?? throw new ArgumentNullException(nameof(dieselConfig));

        if (_loadConfig.ConstantLoadKWhPerHour < 0.0)
            throw new ArgumentOutOfRangeException(nameof(loadConfig.ConstantLoadKWhPerHour));

        if (_dieselConfig.SpecificFuelConsumptionLPerKWh < 0.0)
            throw new ArgumentOutOfRangeException(nameof(dieselConfig.SpecificFuelConsumptionLPerKWh));
    }

    public HybridDispatchResult Dispatch(
        double pvEnergyKWh,
        BatteryState battery,
        bool dieselAvailable)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(pvEnergyKWh, 0.0);
        ArgumentNullException.ThrowIfNull(battery);

        var loadKWh = _loadConfig.ConstantLoadKWhPerHour;
        var socEndOfPreviousHour = battery.SocKWh;

        var coveredByPvKWh = Math.Min(loadKWh, pvEnergyKWh);
        var remainingLoadAfterPvKWh = loadKWh - coveredByPvKWh;
        var pvSurplusKWh = pvEnergyKWh - coveredByPvKWh;

        var chargeResult = battery.Charge(pvSurplusKWh);
        var dischargeResult = battery.DischargeToLoad(remainingLoadAfterPvKWh);

        var coveredByBatteryKWh = dischargeResult.EnergyDeliveredToLoadKWh;
        var remainingLoadAfterBatteryKWh = dischargeResult.UncoveredLoadKWh;

        var coveredByDieselKWh = dieselAvailable
            ? remainingLoadAfterBatteryKWh
            : 0.0;

        var unservedEnergyKWh = remainingLoadAfterBatteryKWh - coveredByDieselKWh;
        var fuelUsedL = coveredByDieselKWh * _dieselConfig.SpecificFuelConsumptionLPerKWh;

        var batteryMetrics = new BatteryHourMetrics(
            SocKWh: battery.SocKWh,
            ChargeKWh: chargeResult.EnergyAcceptedKWh,
            DischargeKWh: dischargeResult.EnergyDeliveredToLoadKWh,
            IsFull: battery.IsFull,
            IsEmpty: battery.IsEmpty);

        var coverageMetrics = new LoadCoverageMetrics(
            CoveredByPvKWh: coveredByPvKWh,
            CoveredByBatteryKWh: coveredByBatteryKWh,
            CoveredByDieselKWh: coveredByDieselKWh,
            UnservedEnergyKWh: unservedEnergyKWh);

        return new HybridDispatchResult(
            Battery: batteryMetrics,
            Coverage: coverageMetrics,
            FuelUsedL: fuelUsedL,
            CurtailmentKWh: chargeResult.EnergyRejectedKWh);
    }
}
