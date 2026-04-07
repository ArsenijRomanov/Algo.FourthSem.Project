using Model.Core.Abstractions;
using Model.Core.Components;
using Model.Core.Components.Results;
using Model.Core.Configs;
using Model.Core.Enums;
using Model.Core.Results;
using Model.Core.Results.FullRun;
using Model.Core.Results.PerHour;
using Model.Core.States;

namespace Model.Core.Simulation;

public sealed class ColdStandbyDieselSimulator : IColdStandbyDieselSimulator
{
    private readonly ColdStandbyScenarioConfig _config;
    private readonly DieselFailureModel _primaryFailureModel;
    private readonly DieselFailureModel _reserveFailureModel;
    private readonly ColdStandbyDispatcher _dispatcher;

    public ColdStandbyDieselSimulator(ColdStandbyScenarioConfig config)
        : this(config, new SystemRandomSource())
    {
    }

    public ColdStandbyDieselSimulator(
        ColdStandbyScenarioConfig config,
        IRandomSource random)
    {
        _config = config ?? throw new ArgumentNullException(nameof(config));
        ArgumentNullException.ThrowIfNull(random);

        var primaryRepairSampler = new TriangularRepairTimeSampler(
            random,
            _config.PrimaryDiesel.RepairTimeHours);

        var reserveRepairSampler = new TriangularRepairTimeSampler(
            random,
            _config.ReserveDiesel.RepairTimeHours);

        _primaryFailureModel = new DieselFailureModel(
            _config.PrimaryDiesel,
            random,
            primaryRepairSampler);

        _reserveFailureModel = new DieselFailureModel(
            _config.ReserveDiesel,
            random,
            reserveRepairSampler);

        _dispatcher = new ColdStandbyDispatcher(
            _config.Load,
            _config.PrimaryDiesel,
            _config.ReserveDiesel);
    }

    public SimulationResult<ColdStandbyHourResult, ColdStandbyRunSummary> Run(
        IReadOnlyList<WeatherPoint> weather)
    {
        ArgumentNullException.ThrowIfNull(weather);

        var state = CreateInitialState();
        var hours = new List<ColdStandbyHourResult>(weather.Count);
        var summaryAccumulator = new ColdStandbySummaryAccumulator();

        foreach (var point in weather)
        {
            var hourResult = SimulateHour(point, state);
            hours.Add(hourResult);
            summaryAccumulator.Add(hourResult);
        }

        return new SimulationResult<ColdStandbyHourResult, ColdStandbyRunSummary>(
            Hours: hours,
            Summary: summaryAccumulator.Build());
    }

    private ColdStandbyHourResult SimulateHour(
    WeatherPoint weather,
    ColdStandbyState state)
{
    var preferred = ColdStandbyDispatcher.SelectActiveDiesel(
        state.ActiveDiesel,
        primaryAvailable: state.Primary.RepairHoursLeft == 0,
        reserveAvailable: state.Reserve.RepairHoursLeft == 0);

    DieselAvailabilityResult primaryAvailability;
    DieselAvailabilityResult reserveAvailability;
    ActiveDieselKind activeDieselForHour;

    switch (preferred)
    {
        case ActiveDieselKind.Primary:
        {
            primaryAvailability = _primaryFailureModel.AdvanceOneHour(
                state.Primary,
                willRunThisHour: true);

            if (primaryAvailability.IsAvailableThisHour)
            {
                reserveAvailability = _reserveFailureModel.AdvanceOneHour(
                    state.Reserve,
                    willRunThisHour: false);

                activeDieselForHour = ActiveDieselKind.Primary;
            }
            else
            {
                reserveAvailability = _reserveFailureModel.AdvanceOneHour(
                    state.Reserve,
                    willRunThisHour: true);

                activeDieselForHour = reserveAvailability.IsAvailableThisHour
                    ? ActiveDieselKind.Reserve
                    : ActiveDieselKind.None;
            }

            break;
        }

        case ActiveDieselKind.Reserve:
        {
            reserveAvailability = _reserveFailureModel.AdvanceOneHour(
                state.Reserve,
                willRunThisHour: true);

            if (reserveAvailability.IsAvailableThisHour)
            {
                primaryAvailability = _primaryFailureModel.AdvanceOneHour(
                    state.Primary,
                    willRunThisHour: false);

                activeDieselForHour = ActiveDieselKind.Reserve;
            }
            else
            {
                primaryAvailability = _primaryFailureModel.AdvanceOneHour(
                    state.Primary,
                    willRunThisHour: true);

                activeDieselForHour = primaryAvailability.IsAvailableThisHour
                    ? ActiveDieselKind.Primary
                    : ActiveDieselKind.None;
            }

            break;
        }

        default:
        {
            primaryAvailability = _primaryFailureModel.AdvanceOneHour(
                state.Primary,
                willRunThisHour: false);

            reserveAvailability = _reserveFailureModel.AdvanceOneHour(
                state.Reserve,
                willRunThisHour: false);

            activeDieselForHour = ActiveDieselKind.None;
            break;
        }
    }

    state.ActiveDiesel = activeDieselForHour == ActiveDieselKind.None
        ? state.ActiveDiesel
        : activeDieselForHour;

    var loadKWh = _config.Load.ConstantLoadKWhPerHour;

    var coveredByDieselKWh = activeDieselForHour == ActiveDieselKind.None
        ? 0.0
        : loadKWh;

    var unservedEnergyKWh = loadKWh - coveredByDieselKWh;

    var primaryFuelUsedL = activeDieselForHour == ActiveDieselKind.Primary
        ? loadKWh * _config.PrimaryDiesel.SpecificFuelConsumptionLPerKWh
        : 0.0;

    var reserveFuelUsedL = activeDieselForHour == ActiveDieselKind.Reserve
        ? loadKWh * _config.ReserveDiesel.SpecificFuelConsumptionLPerKWh
        : 0.0;

    var primaryMetrics = new DieselHourMetrics(
        IsAvailable: primaryAvailability.IsAvailableThisHour,
        FailedThisHour: primaryAvailability.FailedThisHour,
        RecoveredThisHour: primaryAvailability.RecoveredThisHour,
        RepairHoursLeft: primaryAvailability.RepairHoursLeftEndOfHour,
        FuelUsedL: primaryFuelUsedL);

    var reserveMetrics = new DieselHourMetrics(
        IsAvailable: reserveAvailability.IsAvailableThisHour,
        FailedThisHour: reserveAvailability.FailedThisHour,
        RecoveredThisHour: reserveAvailability.RecoveredThisHour,
        RepairHoursLeft: reserveAvailability.RepairHoursLeftEndOfHour,
        FuelUsedL: reserveFuelUsedL);

    var coverage = new LoadCoverageMetrics(
        CoveredByPvKWh: 0.0,
        CoveredByBatteryKWh: 0.0,
        CoveredByDieselKWh: coveredByDieselKWh,
        UnservedEnergyKWh: unservedEnergyKWh);

    return new ColdStandbyHourResult(
        TimestampMsk: weather.TimestampMsk,
        Primary: primaryMetrics,
        Reserve: reserveMetrics,
        ActiveDiesel: activeDieselForHour,
        Coverage: coverage);
}

    private static ColdStandbyState CreateInitialState()
    {
        var primary = new DieselState();
        var reserve = new DieselState();

        return new ColdStandbyState(
            primary: primary,
            reserve: reserve,
            activeDiesel: ActiveDieselKind.Primary);
    }
}
