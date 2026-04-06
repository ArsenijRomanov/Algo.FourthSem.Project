namespace Model.Core.Configs;

public sealed record DieselConfig(
    double SpecificFuelConsumptionLPerKWh,          // удельный расход топлива
    double FailureProbabilityPerMonth,              // месячная вероятность отказа 
    TriangularDistributionConfig RepairTimeHours);  // время починки
    