using MongoDB.Bson;
using MongoDB.Bson.Serialization.Conventions;

namespace API.Data;

public static class MongoConventions
{
    private static int _registered;

    /// <summary>camelCase, enums en chaînes, champs inconnus ignorés. À appeler avant tout accès à Mongo.</summary>
    public static void Register()
    {
        if (Interlocked.Exchange(ref _registered, 1) == 1)
            return;

        var pack = new ConventionPack
        {
            new CamelCaseElementNameConvention(),
            new EnumRepresentationConvention(BsonType.String),
            new IgnoreExtraElementsConvention(true)
        };
        ConventionRegistry.Register("ApiConventions", pack, t => t.Namespace?.StartsWith("API") == true);
    }
}
