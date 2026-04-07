namespace Model.Core.Components.Results;

public sealed record PvCalculationResult(
    double TCellC,
    double Efficiency,
    double PPvKW,
    double EPvKWh);
    