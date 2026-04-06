namespace Model.Core.Results.PerHour;

public sealed record PvHourMetrics(
    double GtiWm2,          // сколько солнечной радиации пришло на наклонную панель в этот час
    double TAirC,           // температура воздуха в этот час
    double WindMs,          // скорость ветра в этот час
    double TCellC,          // температура самой панели
    double PPvKW,           // мощность солнечной станции в этот час
    double EPvKWh);          // сколько энергии солнечная станция дала за этот час
    