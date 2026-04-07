namespace Model.Core.Components.Results;

public sealed record DieselAvailabilityResult(
    bool IsAvailableThisHour,
    bool FailedThisHour,
    bool RecoveredThisHour,
    int RepairHoursLeftEndOfHour);
    