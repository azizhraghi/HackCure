using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace API.Entites;

/// <summary>Compte d'authentification, commun à tous les rôles.</summary>
public class User
{
    [BsonId, BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = ObjectId.GenerateNewId().ToString();

    /// <summary>Toujours stocké en minuscules (index unique).</summary>
    public string Email { get; set; } = null!;

    public string PasswordHash { get; set; } = null!;

    public UserRole Role { get; set; }

    public string FirstName { get; set; } = null!;

    public string LastName { get; set; } = null!;

    public string? Phone { get; set; }

    /// <summary>Numéro international, chiffres uniquement, sans "+" (format attendu par l'API WhatsApp Cloud).</summary>
    public string? WhatsappNumber { get; set; }

    /// <summary>Token Firebase Cloud Messaging du dernier appareil connecté.</summary>
    public string? FcmToken { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [BsonIgnore]
    public string FullName => $"{FirstName} {LastName}";
}
