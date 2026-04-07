using Model.Core.Abstractions;

namespace Model.Core.Components;

public sealed class SystemRandomSource(Random random) : IRandomSource
{
    private readonly Random _random = random ?? throw new ArgumentNullException(nameof(random));

    public SystemRandomSource()
        : this(new Random())
    {
    }

    public SystemRandomSource(int seed)
        : this(new Random(seed))
    {
    }

    public double NextDouble() => _random.NextDouble();
}
