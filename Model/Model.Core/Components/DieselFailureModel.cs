using Model.Core.Abstractions;
using Model.Core.Components.Results;
using Model.Core.Configs;
using Model.Core.States;

namespace Model.Core.Components;

public sealed class DieselFailureModel
{
    private const double DefaultHoursInMonth = 720.0;

    private readonly DieselConfig _config;
    private readonly IRandomSource _random;
    private readonly IRepairTimeSampler _repairTimeSampler;

    public DieselFailureModel(
        DieselConfig config,
        IRandomSource random,
        IRepairTimeSampler repairTimeSampler)
    {
        _config = config ?? throw new ArgumentNullException(nameof(config));
        _random = random ?? throw new ArgumentNullException(nameof(random));
        _repairTimeSampler = repairTimeSampler ?? throw new ArgumentNullException(nameof(repairTimeSampler));

        if (_config.FailureProbabilityPerMonth < 0.0 || _config.FailureProbabilityPerMonth >= 1.0)
            throw new ArgumentOutOfRangeException(nameof(config.FailureProbabilityPerMonth));

        if (_config.SpecificFuelConsumptionLPerKWh < 0.0)
            throw new ArgumentOutOfRangeException(nameof(config.SpecificFuelConsumptionLPerKWh));
    }

    public double SpecificFuelConsumptionLPerKWh => _config.SpecificFuelConsumptionLPerKWh;

    public DieselAvailabilityResult AdvanceOneHour(
        DieselState state,
        bool willRunThisHour)
    {
        ArgumentNullException.ThrowIfNull(state);

        // если в ремонте — ремонт идёт в любом случае
        if (state.RepairHoursLeft > 0)
        {
            var recoveredThisHour = state.AdvanceRepairHour();

            return new DieselAvailabilityResult(
                IsAvailableThisHour: false,
                FailedThisHour: false,
                RecoveredThisHour: recoveredThisHour,
                RepairHoursLeftEndOfHour: state.RepairHoursLeft);
        }

        // здоров, но в этом часу не использовался — не ломаем
        if (!willRunThisHour)
        {
            return new DieselAvailabilityResult(
                IsAvailableThisHour: true,
                FailedThisHour: false,
                RecoveredThisHour: false,
                RepairHoursLeftEndOfHour: 0);
        }

        // здоров и используется — моделируем отказ
        var hourlyFailureProbability = CalculateHourlyFailureProbability(_config.FailureProbabilityPerMonth);
        var failedThisHour = _random.NextDouble() < hourlyFailureProbability;

        if (!failedThisHour)
        {
            return new DieselAvailabilityResult(
                IsAvailableThisHour: true,
                FailedThisHour: false,
                RecoveredThisHour: false,
                RepairHoursLeftEndOfHour: 0);
        }

        var sampledRepairHours = _repairTimeSampler.SampleHours();
        var repairHoursForNextHours = Math.Max(sampledRepairHours - 1, 0);

        state.StartRepair(repairHoursForNextHours);

        return new DieselAvailabilityResult(
            IsAvailableThisHour: false,
            FailedThisHour: true,
            RecoveredThisHour: false,
            RepairHoursLeftEndOfHour: state.RepairHoursLeft);
    }

    public static double CalculateHourlyFailureProbability(double monthlyFailureProbability)
    {
        return monthlyFailureProbability switch
        {
            < 0.0 or >= 1.0 => throw new ArgumentOutOfRangeException(nameof(monthlyFailureProbability)),
            0.0 => 0.0,
            _ => 1.0 - Math.Pow(1.0 - monthlyFailureProbability, 1.0 / DefaultHoursInMonth)
        };
    }
}
