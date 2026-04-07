using Model.Core.Abstractions;
using Model.Core.Configs;

namespace Model.Core.Components;

public sealed class TriangularRepairTimeSampler : IRepairTimeSampler
{
    private readonly IRandomSource _random;
    private readonly TriangularDistributionConfig _config;

    public TriangularRepairTimeSampler(
        IRandomSource random,
        TriangularDistributionConfig config)
    {
        _random = random ?? throw new ArgumentNullException(nameof(random));
        _config = config ?? throw new ArgumentNullException(nameof(config));

        if (_config.Min > _config.Mode || _config.Mode > _config.Max)
            throw new ArgumentException("Triangular distribution parameters are invalid.");
    }

    public int SampleHours()
    {
        var a = _config.Min;
        var c = _config.Mode;
        var b = _config.Max;

        if (Math.Abs(b - a) < double.Epsilon)
            return Math.Max(1, (int)Math.Ceiling(a));

        var u = _random.NextDouble();
        var f = (c - a) / (b - a);

        var sample = u < f
            ? a + Math.Sqrt(u * (b - a) * (c - a))
            : b - Math.Sqrt((1.0 - u) * (b - a) * (b - c));

        return Math.Max(1, (int)Math.Ceiling(sample));
    }
}