using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace API.Entites;

public enum IntakeStatus
{
    Taken,
    Skipped
}

/// <summary>Statut d'une prise planifiée : PENDING (à venir), MISSED (heure passée sans réponse) ou celui enregistré par le patient.</summary>
public enum DoseStatus
{
    Pending,
    Taken,
    Skipped,
    Missed
}

/// <summary>
/// Traitement prescrit par un médecin/infirmier. Les horaires sont des heures locales du patient (« HH:mm »),
/// les dates des jours locaux (« yyyy-MM-dd ») : aucun calcul de fuseau côté serveur.
/// </summary>
public class Medication
{
    [BsonId, BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = ObjectId.GenerateNewId().ToString();

    [BsonRepresentation(BsonType.ObjectId)]
    public string PatientId { get; set; } = null!;

    public string Name { get; set; } = null!;
    public string? Dosage { get; set; }
    public string? Instructions { get; set; }

    /// <summary>Heures de prise quotidiennes, triées, « HH:mm ».</summary>
    public List<string> Times { get; set; } = [];

    public string StartDate { get; set; } = null!;

    /// <summary>Dernier jour de traitement inclus ; null = sans limite.</summary>
    public string? EndDate { get; set; }

    public bool Active { get; set; } = true;

    [BsonRepresentation(BsonType.ObjectId)]
    public string PrescribedByUserId { get; set; } = null!;

    public string PrescribedByName { get; set; } = null!;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

/// <summary>Réponse du patient pour une prise (médicament + jour + heure). Unique par prise.</summary>
public class MedicationIntake
{
    [BsonId, BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = ObjectId.GenerateNewId().ToString();

    [BsonRepresentation(BsonType.ObjectId)]
    public string MedicationId { get; set; } = null!;

    [BsonRepresentation(BsonType.ObjectId)]
    public string PatientId { get; set; } = null!;

    public string Date { get; set; } = null!;
    public string Time { get; set; } = null!;
    public IntakeStatus Status { get; set; }
    public DateTime RecordedAt { get; set; } = DateTime.UtcNow;
}
