using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace API.Entites;

/// <summary>Alerte émise par le Système Multi-Agent, avec l'historique des notifications envoyées.</summary>
public class AlertLog
{
    [BsonId, BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = ObjectId.GenerateNewId().ToString();

    [BsonRepresentation(BsonType.ObjectId)]
    public string PatientId { get; set; } = null!;

    public AlertType Type { get; set; }

    /// <summary>1 = surveillance, 2 = urgent, 3 = critique.</summary>
    public int Severity { get; set; }

    public string Message { get; set; } = null!;

    /// <summary>Nom de l'agent émetteur.</summary>
    public string? Source { get; set; }

    /// <summary>Valeurs mesurées au moment de l'alerte.</summary>
    public VitalsSnapshot? Vitals { get; set; }

    public AlertStatus Status { get; set; } = AlertStatus.Open;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public List<NotificationRecord> Notifications { get; set; } = [];
}

public class VitalsSnapshot
{
    public DateTime? Timestamp { get; set; }
    public int? Bpm { get; set; }
    public double? Spo2 { get; set; }
    public double? RoomTemp { get; set; }
    public double? RoomHumidity { get; set; }
    public bool? FallDetected { get; set; }
}

public class NotificationRecord
{
    [BsonRepresentation(BsonType.ObjectId)]
    public string RecipientUserId { get; set; } = null!;

    public string RecipientName { get; set; } = null!;

    public NotificationChannel Channel { get; set; }

    /// <summary>Numéro WhatsApp, ou token FCM tronqué.</summary>
    public string Target { get; set; } = null!;

    public bool Success { get; set; }

    /// <summary>True si le canal est désactivé dans la config : l'envoi est seulement journalisé.</summary>
    public bool Simulated { get; set; }

    public string? ProviderMessageId { get; set; }

    public string? Error { get; set; }

    public DateTime SentAt { get; set; } = DateTime.UtcNow;
}
