namespace Model.Core.Results.PerHour;

public sealed record LoadCoverageMetrics(
    double CoveredByPvKWh,          // сколько нагрузки покрыли панели напрямую
    double CoveredByBatteryKWh,     // сколько нагрузки покрыла АКБ
    double CoveredByDieselKWh,      // сколько нагрузки покрыл дизель
    double UnservedEnergyKWh        // сколько нагрузки осталось непокрытым
    ) 
{
    public bool LoadFullyCovered => UnservedEnergyKWh <= 0.0;
    public bool SystemDown => UnservedEnergyKWh > 0.0;
}
