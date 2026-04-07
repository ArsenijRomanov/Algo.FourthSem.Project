using Model.Core.Components.Results;
using Model.Core.Configs;
using Model.Core.Enums;
using Model.Core.Results.PerHour;

namespace Model.Core.Components;

public sealed class ColdStandbyDispatcher
{
    private readonly LoadConfig _loadConfig;
    private readonly DieselConfig _primaryDieselConfig;
    private readonly DieselConfig _reserveDieselConfig;

    public ColdStandbyDispatcher(
        LoadConfig loadConfig,
        DieselConfig primaryDieselConfig,
        DieselConfig reserveDieselConfig)
    {
        _loadConfig = loadConfig ?? throw new ArgumentNullException(nameof(loadConfig));
        _primaryDieselConfig = primaryDieselConfig ?? throw new ArgumentNullException(nameof(primaryDieselConfig));
        _reserveDieselConfig = reserveDieselConfig ?? throw new ArgumentNullException(nameof(reserveDieselConfig));

        if (_loadConfig.ConstantLoadKWhPerHour < 0.0)
            throw new ArgumentOutOfRangeException(nameof(loadConfig.ConstantLoadKWhPerHour));
    }

    public ColdStandbyDispatchResult Dispatch(
        ActiveDieselKind currentActive,
        bool primaryAvailable,
        bool reserveAvailable)
    {
        var activeDiesel = SelectActiveDiesel(
            currentActive,
            primaryAvailable,
            reserveAvailable);

        var loadKWh = _loadConfig.ConstantLoadKWhPerHour;

        var primaryFuelUsedL = 0.0;
        var reserveFuelUsedL = 0.0;
        var coveredByDieselKWh = 0.0;
        var unservedEnergyKWh = 0.0;

        switch (activeDiesel)
        {
            case ActiveDieselKind.Primary:
                coveredByDieselKWh = loadKWh;
                primaryFuelUsedL = loadKWh * _primaryDieselConfig.SpecificFuelConsumptionLPerKWh;
                break;

            case ActiveDieselKind.Reserve:
                coveredByDieselKWh = loadKWh;
                reserveFuelUsedL = loadKWh * _reserveDieselConfig.SpecificFuelConsumptionLPerKWh;
                break;

            case ActiveDieselKind.None:
            default:
                unservedEnergyKWh = loadKWh;
                break;
        }

        var coverage = new LoadCoverageMetrics(
            CoveredByPvKWh: 0.0,
            CoveredByBatteryKWh: 0.0,
            CoveredByDieselKWh: coveredByDieselKWh,
            UnservedEnergyKWh: unservedEnergyKWh);

        return new ColdStandbyDispatchResult(
            ActiveDiesel: activeDiesel,
            PrimaryFuelUsedL: primaryFuelUsedL,
            ReserveFuelUsedL: reserveFuelUsedL,
            Coverage: coverage);
    }

    public static ActiveDieselKind SelectActiveDiesel(
        ActiveDieselKind currentActive,
        bool primaryAvailable,
        bool reserveAvailable)
    {
        return currentActive switch
        {
            ActiveDieselKind.Primary when primaryAvailable => ActiveDieselKind.Primary,
            ActiveDieselKind.Reserve when reserveAvailable => ActiveDieselKind.Reserve,
            _ when primaryAvailable => ActiveDieselKind.Primary,
            _ when reserveAvailable => ActiveDieselKind.Reserve,
            _ => ActiveDieselKind.None
        };
    }
}
