namespace Model.Core.Configs;

public sealed record PvSystemConfig(
    double PNomW,                               // номинальная мощность 
    double TempCoefficientGamma,                // температурный коэффициент мощности панели (γ =-0.0035) 
    double ModuleEfficiencyRef,                 // КПД модуля при стандартных условиях (η_ref = 0.204)
    double TauAlpha = 0.9,                      // эффективное произведение пропускания покрытия и поглощения модулем (τα) PVWatts
    double ReferenceCellTemperatureC = 25.0,    // опорная температура ячейки, относительно которой считается температурная поправка мощности PVWatts
    double NoctAdjustedC = 47.0);               // скорректированная номинальная рабочая температура ячейки в стандартных условиях NOCT PVWatts
    