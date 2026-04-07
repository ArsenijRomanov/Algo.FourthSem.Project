using Model.Core.States.Battery;

namespace Model.Core.States;

public sealed class HybridSystemState(BatteryState battery, DieselState diesel)
{
    public BatteryState Battery { get; } = battery ?? throw new ArgumentNullException(nameof(battery));

    public DieselState Diesel { get; } = diesel ?? throw new ArgumentNullException(nameof(diesel));
}
