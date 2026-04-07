using Model.Core.Components.Results;
using Model.Core.Configs;

namespace Model.Core.Components;

public sealed class PvCalculator
{
    private readonly PvSystemConfig _config;

    public PvCalculator(PvSystemConfig config)
    {
        _config = config ?? throw new ArgumentNullException(nameof(config));

        if (_config.PNomW < 0.0)
            throw new ArgumentOutOfRangeException(nameof(config.PNomW));

        if (_config.TauAlpha <= 0.0)
            throw new ArgumentOutOfRangeException(nameof(config.TauAlpha));
    }

    public PvCalculationResult Calculate(WeatherPoint weather)
    {
        ArgumentNullException.ThrowIfNull(weather);

        var gti = Math.Max(0.0, weather.GtiWm2);
        var wind = Math.Max(0.0, weather.WindMs);

        var adjustedWind = 0.51 * wind;

        var thermalFactor =
            (_config.NoctAdjustedC - 20.0) *
            (1.0 - _config.ModuleEfficiencyRef / _config.TauAlpha);

        var tCell =
            weather.TAirC +
            (gti / 800.0) *
            thermalFactor *
            9.5 / (5.7 + 3.8 * adjustedWind);

        var efficiency =
            1.0 +
            _config.TempCoefficientGamma * (tCell - _config.ReferenceCellTemperatureC);

        var pPvW =
            _config.PNomW *
            (gti / 1000.0) *
            efficiency;

        var pPvKW = pPvW / 1000.0;
        var ePvKWh = pPvKW; // шаг модели = 1 час

        return new PvCalculationResult(
            TCellC: tCell,
            Efficiency: efficiency,
            PPvKW: pPvKW,
            EPvKWh: ePvKWh);
    }
}
