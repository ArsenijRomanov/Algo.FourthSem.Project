using Model.Core.Enums;
using Model.Core.Results.PerHour;

namespace Model.Core.Components.Results;

public sealed record ColdStandbyDispatchResult(
    ActiveDieselKind ActiveDiesel,
    double PrimaryFuelUsedL,
    double ReserveFuelUsedL,
    LoadCoverageMetrics Coverage);