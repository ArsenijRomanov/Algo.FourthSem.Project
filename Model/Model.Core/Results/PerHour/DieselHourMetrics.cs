namespace Model.Core.Results.PerHour;

public sealed record DieselHourMetrics(
    bool IsAvailable,           // доступен ли дизель в этот час
    bool FailedThisHour,        // сломался ли дизель в этот час
    bool RecoveredThisHour,     // закончился ли ремонт в этот час
    int RepairHoursLeft,        // сколько часов ремонта осталось
    double FuelUsedL);          // сколько топлива сгорело за час
    