using System.Globalization;
using System.Text;
using System.Text.Json;
using Model.Core.Results.FullRun;
using Model.Core.Results.PerHour;

namespace Model.Runner;

public static class ResultWriter
{
    public static void WriteHybridSingleRun(
        string outputDirectory,
        int seed,
        HybridRunSummary summary,
        IReadOnlyList<HybridHourResult> hours)
    {
        Directory.CreateDirectory(outputDirectory);

        WriteJson(
            Path.Combine(outputDirectory, $"hybrid_summary_seed_{seed}.json"),
            summary);

        WriteHybridHoursCsv(
            Path.Combine(outputDirectory, $"hybrid_hours_seed_{seed}.csv"),
            hours);
    }

    public static void WriteColdStandbySingleRun(
        string outputDirectory,
        int seed,
        ColdStandbyRunSummary summary,
        IReadOnlyList<ColdStandbyHourResult> hours)
    {
        Directory.CreateDirectory(outputDirectory);

        WriteJson(
            Path.Combine(outputDirectory, $"coldstandby_summary_seed_{seed}.json"),
            summary);

        WriteColdStandbyHoursCsv(
            Path.Combine(outputDirectory, $"coldstandby_hours_seed_{seed}.csv"),
            hours);
    }

    public static void WriteHybridMonteCarlo(
        string outputDirectory,
        IReadOnlyList<HybridRunSummary> summaries)
    {
        Directory.CreateDirectory(outputDirectory);

        WriteJson(
            Path.Combine(outputDirectory, "hybrid_montecarlo_summaries.json"),
            summaries);
    }

    public static void WriteColdStandbyMonteCarlo(
        string outputDirectory,
        IReadOnlyList<ColdStandbyRunSummary> summaries)
    {
        Directory.CreateDirectory(outputDirectory);

        WriteJson(
            Path.Combine(outputDirectory, "coldstandby_montecarlo_summaries.json"),
            summaries);
    }

    private static void WriteJson<T>(string path, T value)
    {
        var options = new JsonSerializerOptions
        {
            WriteIndented = true
        };

        var json = JsonSerializer.Serialize(value, options);
        File.WriteAllText(path, json, Encoding.UTF8);
    }

    private static void WriteHybridHoursCsv(string path, IReadOnlyList<HybridHourResult> hours)
    {
        var sb = new StringBuilder();

        sb.AppendLine(
            "TimestampMsk,GtiWm2,TAirC,WindMs,TCellC,PPvKW,EPvKWh," +
            "SocKWh,ChargeKWh,DischargeKWh,IsFull,IsEmpty," +
            "DieselIsAvailable,DieselFailedThisHour,DieselRecoveredThisHour,RepairHoursLeft,FuelUsedL," +
            "CoveredByPvKWh,CoveredByBatteryKWh,CoveredByDieselKWh,UnservedEnergyKWh,LoadFullyCovered,SystemDown");

        foreach (var h in hours)
        {
            sb.AppendLine(string.Join(",",
                Escape(h.TimestampMsk.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture)),
                F(h.Pv.GtiWm2),
                F(h.Pv.TAirC),
                F(h.Pv.WindMs),
                F(h.Pv.TCellC),
                F(h.Pv.PPvKW),
                F(h.Pv.EPvKWh),

                F(h.Battery.SocKWh),
                F(h.Battery.ChargeKWh),
                F(h.Battery.DischargeKWh),
                h.Battery.IsFull,
                h.Battery.IsEmpty,

                h.Diesel.IsAvailable,
                h.Diesel.FailedThisHour,
                h.Diesel.RecoveredThisHour,
                h.Diesel.RepairHoursLeft,
                F(h.Diesel.FuelUsedL),

                F(h.Coverage.CoveredByPvKWh),
                F(h.Coverage.CoveredByBatteryKWh),
                F(h.Coverage.CoveredByDieselKWh),
                F(h.Coverage.UnservedEnergyKWh),
                h.Coverage.LoadFullyCovered,
                h.Coverage.SystemDown));
        }

        File.WriteAllText(path, sb.ToString(), Encoding.UTF8);
    }

    private static void WriteColdStandbyHoursCsv(string path, IReadOnlyList<ColdStandbyHourResult> hours)
    {
        var sb = new StringBuilder();

        sb.AppendLine(
            "TimestampMsk,ActiveDiesel," +
            "PrimaryIsAvailable,PrimaryFailedThisHour,PrimaryRecoveredThisHour,PrimaryRepairHoursLeft,PrimaryFuelUsedL," +
            "ReserveIsAvailable,ReserveFailedThisHour,ReserveRecoveredThisHour,ReserveRepairHoursLeft,ReserveFuelUsedL," +
            "CoveredByDieselKWh,UnservedEnergyKWh,LoadFullyCovered,SystemDown");

        foreach (var h in hours)
        {
            sb.AppendLine(string.Join(",",
                Escape(h.TimestampMsk.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture)),
                h.ActiveDiesel,

                h.Primary.IsAvailable,
                h.Primary.FailedThisHour,
                h.Primary.RecoveredThisHour,
                h.Primary.RepairHoursLeft,
                F(h.Primary.FuelUsedL),

                h.Reserve.IsAvailable,
                h.Reserve.FailedThisHour,
                h.Reserve.RecoveredThisHour,
                h.Reserve.RepairHoursLeft,
                F(h.Reserve.FuelUsedL),

                F(h.Coverage.CoveredByDieselKWh),
                F(h.Coverage.UnservedEnergyKWh),
                h.Coverage.LoadFullyCovered,
                h.Coverage.SystemDown));
        }

        File.WriteAllText(path, sb.ToString(), Encoding.UTF8);
    }

    private static string F(double value) =>
        value.ToString("G17", CultureInfo.InvariantCulture);

    private static string Escape(string value)
    {
        if (value.Contains(',') || value.Contains('"') || value.Contains('\n') || value.Contains('\r'))
            return $"\"{value.Replace("\"", "\"\"")}\"";

        return value;
    }
}