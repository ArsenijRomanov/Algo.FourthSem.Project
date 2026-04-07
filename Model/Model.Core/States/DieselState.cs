namespace Model.Core.States;

public sealed class DieselState
{
    public DieselState(bool isAvailable = true, int repairHoursLeft = 0)
    {
        switch (repairHoursLeft)
        {
            case < 0:
                throw new ArgumentOutOfRangeException(nameof(repairHoursLeft));
            case > 0:
                IsAvailable = false;
                RepairHoursLeft = repairHoursLeft;
                return;
            default:
                IsAvailable = isAvailable;
                RepairHoursLeft = 0;
                break;
        }
    }

    public bool IsAvailable { get; private set; }

    /// <summary>
    /// Сколько часов ремонта осталось на начало следующего часа.
    /// </summary>
    public int RepairHoursLeft { get; private set; }

    public void MakeAvailable()
    {
        IsAvailable = true;
        RepairHoursLeft = 0;
    }

    public void StartRepair(int repairHoursLeft)
    {
        if (repairHoursLeft < 0)
            throw new ArgumentOutOfRangeException(nameof(repairHoursLeft));

        IsAvailable = false;
        RepairHoursLeft = repairHoursLeft;
    }

    /// <summary>
    /// Вызывается в конце часа, если дизель был в ремонте весь текущий час.
    /// Возвращает true, если ремонт закончился к концу текущего часа.
    /// </summary>
    public bool AdvanceRepairHour()
    {
        if (RepairHoursLeft <= 0)
            return false;

        RepairHoursLeft--;

        if (RepairHoursLeft == 0)
        {
            IsAvailable = true;
            return true;
        }

        IsAvailable = false;
        return false;
    }
}
