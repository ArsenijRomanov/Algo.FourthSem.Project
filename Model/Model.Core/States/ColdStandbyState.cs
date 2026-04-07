using Model.Core.Enums;

namespace Model.Core.States;

public sealed class ColdStandbyState(
    DieselState primary,
    DieselState reserve,
    ActiveDieselKind activeDiesel = ActiveDieselKind.Primary)
{
    public DieselState Primary { get; } = primary ?? throw new ArgumentNullException(nameof(primary));

    public DieselState Reserve { get; } = reserve ?? throw new ArgumentNullException(nameof(reserve));

    public ActiveDieselKind ActiveDiesel { get; set; } = activeDiesel;
}
