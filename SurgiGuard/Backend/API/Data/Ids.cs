using MongoDB.Bson;

namespace API.Data;

public static class Ids
{
    /// <summary>À vérifier avant de filtrer sur un Id : une chaîne invalide fait échouer la sérialisation en ObjectId.</summary>
    public static bool IsValid(string? id) => id is not null && ObjectId.TryParse(id, out _);
}
