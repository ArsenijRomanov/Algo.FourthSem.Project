namespace Model.Core.Configs;

public sealed record BatteryConfig(
    double NominalCapacityKWh,      // Номинальная емкость АКБ
    double MinAllowedSocKWh,        // Минимальный заряд, до которого можно разряжать
    double ChargeEfficiency,        // КПД заряда
    double DischargeEfficiency,     // КПД разряда
    double InitialSocKWh)           // Начальный заряд
{
    public double MaxAllowedSocKWh => NominalCapacityKWh;
    public double UsableCapacityKWh => MaxAllowedSocKWh - MinAllowedSocKWh;
}