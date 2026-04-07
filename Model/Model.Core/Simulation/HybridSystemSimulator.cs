using Model.Core.Abstractions;
using Model.Core.Components;
using Model.Core.Configs;
using Model.Core.Results;
using Model.Core.Results.FullRun;
using Model.Core.Results.PerHour;
using Model.Core.States;
using Model.Core.States.Battery;

namespace Model.Core.Simulation;

public sealed class HybridSystemSimulator : IHybridSystemSimulator
{
    private readonly HybridScenarioConfig _config;
    private readonly PvCalculator _pvCalculator;
    private readonly DieselFailureModel _dieselFailureModel;
    private readonly HybridDispatcher _dispatcher;

    public HybridSystemSimulator(HybridScenarioConfig config)
        : this(config, new SystemRandomSource())
    {
    }

    public HybridSystemSimulator(
        HybridScenarioConfig config,
        IRandomSource random)
    {
        _config = config ?? throw new ArgumentNullException(nameof(config));
        ArgumentNullException.ThrowIfNull(random);

        _pvCalculator = new PvCalculator(_config.Pv);

        var repairSampler = new TriangularRepairTimeSampler(
            random,
            _config.Diesel.RepairTimeHours);

        _dieselFailureModel = new DieselFailureModel(
            _config.Diesel,
            random,
            repairSampler);

        _dispatcher = new HybridDispatcher(
            _config.Load,
            _config.Diesel);
    }

    public SimulationResult<HybridHourResult, HybridRunSummary> Run(
        IReadOnlyList<WeatherPoint> weather)
    {
        ArgumentNullException.ThrowIfNull(weather);

        var state = CreateInitialState();
        var hours = new List<HybridHourResult>(weather.Count);
        var summaryAccumulator = new HybridSummaryAccumulator();

        foreach (var point in weather)
        {
            var (hourResult, curtailmentKWh) = SimulateHour(point, state);
            hours.Add(hourResult);
            summaryAccumulator.Add(hourResult, curtailmentKWh);
        }

        return new SimulationResult<HybridHourResult, HybridRunSummary>(
            Hours: hours,
            Summary: summaryAccumulator.Build());
    }

    private (HybridHourResult Hour, double CurtailmentKWh) SimulateHour(
    WeatherPoint weather,
    HybridSystemState state)
{
    var pv = _pvCalculator.Calculate(weather);

    // сначала считаем PV + АКБ, дизель пока считаем недоступным
    var dispatchBeforeDiesel = _dispatcher.Dispatch(
        pvEnergyKWh: pv.EPvKWh,
        battery: state.Battery,
        dieselAvailable: false);

    var needDiesel = dispatchBeforeDiesel.Coverage.UnservedEnergyKWh > 0.0;

    var dieselAvailability = _dieselFailureModel.AdvanceOneHour(
        state.Diesel,
        willRunThisHour: needDiesel);

    var coveredByDieselKWh = dieselAvailability.IsAvailableThisHour
        ? dispatchBeforeDiesel.Coverage.UnservedEnergyKWh
        : 0.0;

    var unservedEnergyKWh =
        dispatchBeforeDiesel.Coverage.UnservedEnergyKWh - coveredByDieselKWh;

    var finalCoverage = new LoadCoverageMetrics(
        CoveredByPvKWh: dispatchBeforeDiesel.Coverage.CoveredByPvKWh,
        CoveredByBatteryKWh: dispatchBeforeDiesel.Coverage.CoveredByBatteryKWh,
        CoveredByDieselKWh: coveredByDieselKWh,
        UnservedEnergyKWh: unservedEnergyKWh);

    var fuelUsedL = coveredByDieselKWh * _dieselFailureModel.SpecificFuelConsumptionLPerKWh;

    var pvMetrics = new PvHourMetrics(
        GtiWm2: weather.GtiWm2,
        TAirC: weather.TAirC,
        WindMs: weather.WindMs,
        TCellC: pv.TCellC,
        PPvKW: pv.PPvKW,
        EPvKWh: pv.EPvKWh);

    var batteryMetrics = new BatteryHourMetrics(
        SocKWh: state.Battery.SocKWh,
        ChargeKWh: dispatchBeforeDiesel.Battery.ChargeKWh,
        DischargeKWh: dispatchBeforeDiesel.Battery.DischargeKWh,
        IsFull: dispatchBeforeDiesel.Battery.IsFull,
        IsEmpty: dispatchBeforeDiesel.Battery.IsEmpty);

    var dieselMetrics = new DieselHourMetrics(
        IsAvailable: dieselAvailability.IsAvailableThisHour,
        FailedThisHour: dieselAvailability.FailedThisHour,
        RecoveredThisHour: dieselAvailability.RecoveredThisHour,
        RepairHoursLeft: dieselAvailability.RepairHoursLeftEndOfHour,
        FuelUsedL: fuelUsedL);

    var hour = new HybridHourResult(
        TimestampMsk: weather.TimestampMsk,
        Pv: pvMetrics,
        Battery: batteryMetrics,
        Diesel: dieselMetrics,
        Coverage: finalCoverage);

    return (hour, dispatchBeforeDiesel.CurtailmentKWh);
}

    private HybridSystemState CreateInitialState()
    {
        var battery = new BatteryState(_config.Battery);
        var diesel = new DieselState();

        return new HybridSystemState(battery, diesel);
    }
}
