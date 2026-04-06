namespace Model.Core.Results;

public sealed record SimulationResult<THourResult, TRunSummary>(
    IReadOnlyList<THourResult> Hours,
    TRunSummary Summary);
    