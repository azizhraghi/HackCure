using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace API.Entites;

public class Patient
{
    [BsonId, BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = ObjectId.GenerateNewId().ToString();

    [BsonRepresentation(BsonType.ObjectId)]
    public string UserId { get; set; } = null!;

    public DateTime? DateOfBirth { get; set; }

    public string? Gender { get; set; }

    public string? Address { get; set; }

    /// <summary>Identifiant du boîtier ESP32. Index unique sparse : le champ est absent tant qu'aucun boîtier n'est associé.</summary>
    [BsonIgnoreIfNull]
    public string? DeviceId { get; set; }

    /// <summary>Code unique que le patient partage à sa famille pour lier leurs comptes.</summary>
    public string LinkCode { get; set; } = null!;

    public MedicalFolder MedicalFolder { get; set; } = new();

    public VitalThresholds Thresholds { get; set; } = new();

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public class MedicalFolder
{
    /// <summary>A+, A-, B+, B-, AB+, AB-, O+, O-</summary>
    public string? BloodType { get; set; }

    public List<string> Allergies { get; set; } = [];

    /// <summary>Antécédents médicaux.</summary>
    public List<string> MedicalHistory { get; set; } = [];

    /// <summary>Traitements en cours (ex : "Bisoprolol 5 mg - 1x/jour").</summary>
    public List<string> Medications { get; set; } = [];

    public string? Notes { get; set; }

    /// <summary>PDF stockés dans GridFS (bucket "medicalDocuments").</summary>
    public List<MedicalDocument> Documents { get; set; } = [];

    public DateTime? UpdatedAt { get; set; }
}

public class MedicalDocument
{
    /// <summary>Identifiant du fichier GridFS.</summary>
    [BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = null!;

    public string FileName { get; set; } = null!;

    public long SizeBytes { get; set; }

    public DateTime UploadedAt { get; set; } = DateTime.UtcNow;
}

/// <summary>Seuils personnalisés utilisés pour la détection d'anomalies à l'ingestion.</summary>
public class VitalThresholds
{
    public int MinBpm { get; set; } = 50;

    public int MaxBpm { get; set; } = 120;

    public double MinSpo2 { get; set; } = 92;
}
