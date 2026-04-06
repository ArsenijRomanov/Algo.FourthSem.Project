using Model.Core.Enums;

namespace Model.Core.Results.PerHour;

public sealed record ColdStandbyHourResult(
    DateTime TimestampMsk,
    DieselHourMetrics Primary,
    DieselHourMetrics Reserve,
    ActiveDieselKind ActiveDiesel,
    LoadCoverageMetrics Coverage);
    