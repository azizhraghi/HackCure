namespace API.Settings;

public sealed class MongoDbSettings
{
    public const string SectionName = "MongoDbSettings";

    public string ConnectionString { get; set; } = "";
    public string DatabaseName { get; set; } = "DB";

    /// <summary>Durée de conservation des mesures brutes (TTL de la collection time-series).</summary>
    public int TelemetryRetentionDays { get; set; } = 90;
}

public sealed class JwtSettings
{
    public const string SectionName = "Jwt";

    /// <summary>Clé HMAC-SHA256, 32 caractères minimum.</summary>
    public string Key { get; set; } = "";
    public string Issuer { get; set; } = "health-api";
    public string Audience { get; set; } = "health-mobile";
    public int ExpiryMinutes { get; set; } = 60 * 24 * 7;
}

public sealed class AuthSettings
{
    public const string SectionName = "Auth";

    /// <summary>Code requis pour créer un compte NURSE ou DOCTOR. Vide = inscription du personnel désactivée.</summary>
    public string StaffRegistrationCode { get; set; } = "";
}

/// <summary>Clés des clients machine (passerelle MQTT et Système Multi-Agent), envoyées dans l'en-tête X-Api-Key.</summary>
public sealed class ServiceApiKeysSettings
{
    public const string SectionName = "ServiceApiKeys";

    public string Iot { get; set; } = "";
    public string Agents { get; set; } = "";
}

/// <summary>Broker MQTT (EMQX) sur lequel l'ESP32 publie ses mesures.</summary>
public sealed class MqttSettings
{
    public const string SectionName = "Mqtt";

    public bool Enabled { get; set; }
    public string Broker { get; set; } = "";
    public int Port { get; set; } = 8883;
    public bool UseTls { get; set; } = true;
    public string Username { get; set; } = "";
    public string Password { get; set; } = "";
    public string Topic { get; set; } = "Hackcure/data";

    /// <summary>Boîtier utilisé si le message ne contient pas de device_id.</summary>
    public string? DefaultDeviceId { get; set; }
}

/// <summary>Meta WhatsApp Cloud API.</summary>
public sealed class WhatsAppSettings
{
    public const string SectionName = "WhatsApp";

    /// <summary>False = les messages sont seulement journalisés (mode démo).</summary>
    public bool Enabled { get; set; }
    public string ApiBaseUrl { get; set; } = "https://graph.facebook.com/v20.0";
    public string PhoneNumberId { get; set; } = "";
    public string AccessToken { get; set; } = "";

    /// <summary>
    /// Modèle approuvé avec un paramètre {{1}}. Obligatoire hors fenêtre de 24 h (cas d'une alerte).
    /// Vide = message texte libre, qui ne passe que si le destinataire a écrit au numéro dans les 24 h.
    /// </summary>
    public string? TemplateName { get; set; }
    public string TemplateLanguage { get; set; } = "fr";
}

public sealed class FirebaseSettings
{
    public const string SectionName = "Firebase";

    /// <summary>False = les push sont seulement journalisés (mode démo).</summary>
    public bool Enabled { get; set; }

    /// <summary>Chemin du JSON du compte de service Firebase.</summary>
    public string CredentialsPath { get; set; } = "";
}
