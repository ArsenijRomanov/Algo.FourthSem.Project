namespace Model.Core;

public record WeatherPoint(
    DateTime TimestampMsk,    // время
    double GtiWm2,            // радиация
    double TAirC,             // температура воздуха
    double WindMs             // скорость ветра
    );
    