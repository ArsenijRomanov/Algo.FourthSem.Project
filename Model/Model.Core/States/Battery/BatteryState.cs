using Model.Core.Configs;

namespace Model.Core.States.Battery;

public sealed class BatteryState
{
    private const double Epsilon = 1e-9;
    private readonly BatteryConfig _config;

    public BatteryState(BatteryConfig config)
    {
        _config = config ?? throw new ArgumentNullException(nameof(config));
        ValidateConfig(_config);

        if (_config.InitialSocKWh < _config.MinAllowedSocKWh - Epsilon ||
            _config.InitialSocKWh > _config.MaxAllowedSocKWh + Epsilon)
        {
            throw new ArgumentOutOfRangeException(
                nameof(config),
                "Initial SOC must be within allowed battery bounds.");
        }

        SocKWh = _config.InitialSocKWh;
    }

    public double SocKWh { get; private set; }

    public double MinAllowedSocKWh => _config.MinAllowedSocKWh;
    public double MaxAllowedSocKWh => _config.MaxAllowedSocKWh;
    public double ChargeEfficiency => _config.ChargeEfficiency;
    public double DischargeEfficiency => _config.DischargeEfficiency;

    public bool IsFull => NearlyEqual(SocKWh, MaxAllowedSocKWh);
    public bool IsEmpty => NearlyEqual(SocKWh, MinAllowedSocKWh);

    /// <summary>
    /// offeredEnergyKWh — энергия, которую пытаются направить в АКБ до потерь.
    /// </summary>
    public BatteryChargeResult Charge(double offeredEnergyKWh)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(offeredEnergyKWh, 0.0);

        var freeSocCapacityKWh = Math.Max(0.0, MaxAllowedSocKWh - SocKWh);

        var maxAcceptableInputKWh = freeSocCapacityKWh <= Epsilon
            ? 0.0
            : freeSocCapacityKWh / ChargeEfficiency;

        var acceptedInputKWh = Math.Min(offeredEnergyKWh, maxAcceptableInputKWh);
        var storedInSocKWh = acceptedInputKWh * ChargeEfficiency;
        var rejectedEnergyKWh = offeredEnergyKWh - acceptedInputKWh;

        SocKWh += storedInSocKWh;
        ClampSoc();

        return new BatteryChargeResult(
            EnergyOfferedKWh: offeredEnergyKWh,
            EnergyAcceptedKWh: acceptedInputKWh,
            EnergyStoredInSocKWh: storedInSocKWh,
            EnergyRejectedKWh: rejectedEnergyKWh,
            SocEndKWh: SocKWh);
    }

    /// <summary>
    /// requestedLoadKWh — сколько энергии нужно от АКБ на нагрузку.
    /// </summary>
    public BatteryDischargeResult DischargeToLoad(double requestedLoadKWh)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(requestedLoadKWh, 0.0);

        var removableFromSocKWh = Math.Max(0.0, SocKWh - MinAllowedSocKWh);
        var maxDeliverableToLoadKWh = removableFromSocKWh * DischargeEfficiency;

        var deliveredToLoadKWh = Math.Min(requestedLoadKWh, maxDeliverableToLoadKWh);
        var withdrawnFromSocKWh = deliveredToLoadKWh <= Epsilon
            ? 0.0
            : deliveredToLoadKWh / DischargeEfficiency;

        var uncoveredLoadKWh = requestedLoadKWh - deliveredToLoadKWh;

        SocKWh -= withdrawnFromSocKWh;
        ClampSoc();

        return new BatteryDischargeResult(
            LoadRequestedKWh: requestedLoadKWh,
            EnergyDeliveredToLoadKWh: deliveredToLoadKWh,
            EnergyWithdrawnFromSocKWh: withdrawnFromSocKWh,
            UncoveredLoadKWh: uncoveredLoadKWh,
            SocEndKWh: SocKWh);
    }

    private void ClampSoc()
    {
        if (SocKWh < MinAllowedSocKWh && NearlyEqual(SocKWh, MinAllowedSocKWh))
            SocKWh = MinAllowedSocKWh;

        if (SocKWh > MaxAllowedSocKWh && NearlyEqual(SocKWh, MaxAllowedSocKWh))
            SocKWh = MaxAllowedSocKWh;

        if (SocKWh < MinAllowedSocKWh - Epsilon || SocKWh > MaxAllowedSocKWh + Epsilon)
            throw new InvalidOperationException("Battery SOC went out of allowed bounds.");
    }

    private static void ValidateConfig(BatteryConfig config)
    {
        if (config.NominalCapacityKWh <= 0.0)
            throw new ArgumentOutOfRangeException(nameof(config.NominalCapacityKWh));

        if (config.MinAllowedSocKWh < 0.0 || config.MinAllowedSocKWh > config.NominalCapacityKWh)
            throw new ArgumentOutOfRangeException(nameof(config.MinAllowedSocKWh));

        if (config.ChargeEfficiency is <= 0.0 or > 1.0)
            throw new ArgumentOutOfRangeException(nameof(config.ChargeEfficiency));

        if (config.DischargeEfficiency is <= 0.0 or > 1.0)
            throw new ArgumentOutOfRangeException(nameof(config.DischargeEfficiency));
    }

    private static bool NearlyEqual(double left, double right)
        => Math.Abs(left - right) <= Epsilon;
}
