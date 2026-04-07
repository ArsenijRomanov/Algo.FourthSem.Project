using Model.Runner;

var configPath = args.Length > 0 ? args[0] : "settings.json";

try
{
    var config = AppConfig.Load(configPath);
    var orchestrator = new SimulationOrchestrator();

    orchestrator.Run(config);

    Console.WriteLine("Done.");
}
catch (Exception ex)
{
    Console.Error.WriteLine(ex.ToString());
    Environment.ExitCode = 1;
}
