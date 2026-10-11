using System.Globalization;
using System.Text;
using API.Data;
using API.Dtos;
using API.Entites;
using MongoDB.Driver;

namespace API.Services;

public sealed class AlertService(
    MongoDbContext db,
    IWhatsAppSender whatsapp,
    IPushSender push,
    ILogger<AlertService> logger)
{
    /// <summary>
    /// Enregistre l'alerte puis notifie les proches :
    /// gravité 1 → push ; 2 → push + WhatsApp au contact principal ; 3 → push + WhatsApp à tous les proches opt-in.
    /// Renvoie null si le patient n'existe pas.
    /// </summary>
    public async Task<AlertLog?> TriggerAsync(TriggerAlertRequest request, CancellationToken ct)
    {
        if (!Ids.IsValid(request.PatientId))
            return null;

        var patient = await db.Patients.Find(p => p.Id == request.PatientId).FirstOrDefaultAsync(ct);
        if (patient is null)
            return null;

        var patientUser = await db.Users.Find(u => u.Id == patient.UserId).FirstOrDefaultAsync(ct);

        var alert = new AlertLog
        {
            PatientId = patient.Id,
            Type = request.Type!.Value,
            Severity = request.Severity,
            Message = request.Message.Trim(),
            Source = request.Source,
            Vitals = request.Vitals
        };
        await db.Alerts.InsertOneAsync(alert, cancellationToken: ct);

        logger.LogWarning("Alerte {Type} gravité {Severity} pour le patient {PatientId} ({Source})",
            alert.Type, alert.Severity, alert.PatientId, alert.Source);

        // L'alerte est enregistrée : on notifie jusqu'au bout même si l'appelant coupe la connexion.
        alert.Notifications = await NotifyFamilyAsync(alert, patientUser?.FullName ?? "Patient");
        await db.Alerts.UpdateOneAsync(
            a => a.Id == alert.Id,
            Builders<AlertLog>.Update.Set(a => a.Notifications, alert.Notifications));

        return alert;
    }

    public Task<List<AlertLog>> GetForPatientAsync(string patientId, int limit, CancellationToken ct) =>
        db.Alerts.Find(a => a.PatientId == patientId)
            .SortByDescending(a => a.CreatedAt)
            .Limit(limit)
            .ToListAsync(ct);

    private async Task<List<NotificationRecord>> NotifyFamilyAsync(AlertLog alert, string patientName)
    {
        var relations = await db.PatientFamilyRelations.Find(r => r.PatientId == alert.PatientId).ToListAsync();
        if (relations.Count == 0)
            return [];

        var userIds = relations.Select(r => r.FamilyUserId).ToList();
        var users = (await db.Users.Find(Builders<User>.Filter.In(u => u.Id, userIds)).ToListAsync())
            .ToDictionary(u => u.Id);

        var title = AlertMessages.Title(alert, patientName);
        var whatsappText = AlertMessages.WhatsappText(alert, patientName);
        var data = new Dictionary<string, string>
        {
            ["alert_id"] = alert.Id,
            ["patient_id"] = alert.PatientId,
            ["type"] = alert.Type.ToString().ToUpperInvariant(),
            ["severity"] = alert.Severity.ToString(CultureInfo.InvariantCulture)
        };

        var sends = new List<Task<NotificationRecord>>();
        foreach (var relation in relations)
        {
            if (!users.TryGetValue(relation.FamilyUserId, out var user))
                continue;

            if (!string.IsNullOrEmpty(user.FcmToken))
                sends.Add(Record(user, NotificationChannel.Push, MaskToken(user.FcmToken),
                    push.SendAsync(user.FcmToken, title, alert.Message, data, CancellationToken.None)));

            if (ShouldSendWhatsapp(alert.Severity, relation) && !string.IsNullOrEmpty(user.WhatsappNumber))
                sends.Add(Record(user, NotificationChannel.Whatsapp, user.WhatsappNumber,
                    whatsapp.SendAsync(user.WhatsappNumber, whatsappText, CancellationToken.None)));
        }

        return [.. await Task.WhenAll(sends)];
    }

    private static bool ShouldSendWhatsapp(int severity, PatientFamilyRelation relation) =>
        relation.WhatsappOptIn && (severity >= 3 || (severity == 2 && relation.IsPrimaryContact));

    private static async Task<NotificationRecord> Record(User user, NotificationChannel channel, string target, Task<NotificationResult> send)
    {
        var result = await send;
        return new NotificationRecord
        {
            RecipientUserId = user.Id,
            RecipientName = user.FullName,
            Channel = channel,
            Target = target,
            Success = result.Success,
            Simulated = result.Simulated,
            ProviderMessageId = result.ProviderMessageId,
            Error = result.Error
        };
    }

    private static string MaskToken(string token) => token.Length <= 12 ? token : $"{token[..6]}…{token[^6..]}";
}

public static class AlertMessages
{
    public static string Label(AlertType type) => type switch
    {
        AlertType.Fall => "Chute détectée",
        AlertType.Tachycardia => "Tachycardie",
        AlertType.Bradycardia => "Bradycardie",
        AlertType.Hypoxia => "Hypoxie (SpO2 basse)",
        _ => type.ToString()
    };

    public static string Icon(int severity) => severity switch
    {
        >= 3 => "🚨",
        2 => "⚠️",
        _ => "ℹ️"
    };

    public static string Title(AlertLog alert, string patientName) =>
        $"{Icon(alert.Severity)} {Label(alert.Type)} - {patientName}";

    public static string WhatsappText(AlertLog alert, string patientName)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"{Icon(alert.Severity)} ALERTE SANTÉ - gravité {alert.Severity}/3");
        sb.AppendLine($"Patient : {patientName}");
        sb.AppendLine($"Type : {Label(alert.Type)}");
        sb.AppendLine(alert.Message);

        if (alert.Vitals is { } v)
        {
            var parts = new List<string>();
            if (v.Bpm is { } bpm) parts.Add($"BPM : {bpm}");
            if (v.Spo2 is { } spo2) parts.Add($"SpO2 : {spo2:0.#} %");
            if (v.RoomTemp is { } temp) parts.Add($"Temp. pièce : {temp:0.#} °C");
            if (parts.Count > 0)
                sb.AppendLine(string.Join(" | ", parts));
        }

        sb.Append(CultureInfo.InvariantCulture, $"Heure : {alert.CreatedAt:dd/MM/yyyy HH:mm} UTC");
        return sb.ToString();
    }
}
