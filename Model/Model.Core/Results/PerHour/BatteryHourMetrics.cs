namespace Model.Core.Results.PerHour;

public sealed record BatteryHourMetrics(
    double SocKWh,          // сколько энергии осталось в АКБ на конец часа
    double ChargeKWh,       // сколько энергии АКБ получила за час
    double DischargeKWh,    // сколько энергии АКБ отдала за час
    bool IsFull,            // была ли батарея полной к концу часа
    bool IsEmpty);          // была ли батарея разряжена до допустимого минимума к концу часа
    