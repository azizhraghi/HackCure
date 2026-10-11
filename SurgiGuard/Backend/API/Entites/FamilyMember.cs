using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace API.Entites;

/// <summary>
/// Profil d'un proche. Ce qui dépend du lien avec un patient précis (parenté, opt-in WhatsApp,
/// contact principal) est dans <see cref="PatientFamilyRelation"/>, car un proche peut suivre plusieurs patients.
/// </summary>
public class FamilyMember
{
    [BsonId, BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = ObjectId.GenerateNewId().ToString();

    [BsonRepresentation(BsonType.ObjectId)]
    public string UserId { get; set; } = null!;

    public string? Address { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
