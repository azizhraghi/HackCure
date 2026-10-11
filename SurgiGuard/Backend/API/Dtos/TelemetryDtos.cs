using System.ComponentModel.DataAnnotations;
using API.Entites;

namespace API.Dtos;

/// <summary>Message publié par l'ESP32 et relayé depuis le broker MQTT. device_id OU patient_id est requis.</summary>
public sealed record TelemetryIngestRequest
{
    [MaxLength(64)]
    public string? DeviceId { get; init; }

    public string? PatientId { get; init; }

    /// <summary>Optionnel : l'heure serveur est utilisée si l'ESP32 n'a pas d'horloge synchronisée.</summary>
    public DateTime? Timestamp { get; init; }

    [Range(0, 300)]
    public int? Bpm { get; init; }

    [Range(0, 100)]
    public double? Spo2 { get; init; }

    [Range(-40, 85)]
    public double? RoomTemp { get; init; }

    [Range(0, 100)]
    public double? RoomHumidity { get; init; }

    [MaxLength(32)]
    public string? MotionState { get; init; }

    public bool FallDetected { get; init; }
}

/// <param name="Anomalies">Dépassements des seuils personnalisés, transmis à titre indicatif au Système Multi-Agent.</param>
public sealed record TelemetryIngestResponse(string PatientId, DateTime Timestamp, IReadOnlyList<AlertType> Anomalies);

public sealed record TelemetryDto(
    DateTime Timestamp,
    string? DeviceId,
    int? Bpm,
    double? Spo2,
    double? RoomTemp,
    double? RoomHumidity,
    string? MotionState,
    bool FallDetected)
{
    public static TelemetryDto From(TelemetryReading r) =>
        new(r.Timestamp, r.DeviceId, r.Bpm, r.Spo2, r.RoomTemp, r.RoomHumidity, r.MotionState, r.FallDetected);
}

/// <summary>Point de graphique : moyenne sur l'intervalle (ou mesure brute si interval_minutes = 0).</summary>
public sealed record TelemetryPointDto(
    DateTime Timestamp,
    double? Bpm,
    double? Spo2,
    double? RoomTemp,
    double? RoomHumidity,
    bool FallDetected,
    int Samples);

public sealed record TelemetryHistoryResponse(
    string PatientId,
    DateTime From,
    DateTime To,
    int IntervalMinutes,
    IReadOnlyList<TelemetryPointDto> Points);
