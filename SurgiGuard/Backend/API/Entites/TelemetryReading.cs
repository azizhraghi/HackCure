using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace API.Entites;

/// <summary>Mesure IoT, stockée dans une collection time-series (timeField = timestamp, metaField = patientId).</summary>
public class TelemetryReading
{
    [BsonId]
    public ObjectId Id { get; set; } = ObjectId.GenerateNewId();

    [BsonRepresentation(BsonType.ObjectId)]
    public string PatientId { get; set; } = null!;

    public string? DeviceId { get; set; }

    public DateTime Timestamp { get; set; }

    [BsonIgnoreIfNull]
    public int? Bpm { get; set; }

    [BsonIgnoreIfNull]
    public double? Spo2 { get; set; }

    [BsonIgnoreIfNull]
    public double? RoomTemp { get; set; }

    [BsonIgnoreIfNull]
    public double? RoomHumidity { get; set; }

    /// <summary>État de mouvement remonté par l'accéléromètre (ex : "STILL", "WALKING", "LYING").</summary>
    [BsonIgnoreIfNull]
    public string? MotionState { get; set; }

    public bool FallDetected { get; set; }
}
