using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace API.Entites;

/// <summary>Lien N-N patient / proche (index unique sur PatientId + FamilyMemberId).</summary>
public class PatientFamilyRelation
{
    [BsonId, BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = ObjectId.GenerateNewId().ToString();

    [BsonRepresentation(BsonType.ObjectId)]
    public string PatientId { get; set; } = null!;

    [BsonRepresentation(BsonType.ObjectId)]
    public string FamilyMemberId { get; set; } = null!;

    /// <summary>Dénormalisé pour retrouver directement le compte à notifier.</summary>
    [BsonRepresentation(BsonType.ObjectId)]
    public string FamilyUserId { get; set; } = null!;

    /// <summary>Lien de parenté (ex : "fille", "fils", "conjoint").</summary>
    public string Relationship { get; set; } = null!;

    /// <summary>Consentement à recevoir les alertes par WhatsApp.</summary>
    public bool WhatsappOptIn { get; set; }

    /// <summary>Un seul contact principal par patient.</summary>
    public bool IsPrimaryContact { get; set; }

    public DateTime LinkedAt { get; set; } = DateTime.UtcNow;
}
