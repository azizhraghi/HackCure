using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using API.Settings;
using FirebaseAdmin;
using FirebaseAdmin.Messaging;
using Google.Apis.Auth.OAuth2;
using Microsoft.Extensions.Options;

namespace API.Services;

public sealed record NotificationResult(bool Success, bool Simulated, string? ProviderMessageId, string? Error)
{
    public static NotificationResult Sent(string? providerMessageId) => new(true, false, providerMessageId, null);
    public static NotificationResult Simulate() => new(true, true, null, null);
    public static NotificationResult Failed(string error) => new(false, false, null, error);
}

public interface IWhatsAppSender
{
    Task<NotificationResult> SendAsync(string to, string message, CancellationToken ct);
}

public interface IPushSender
{
    Task<NotificationResult> SendAsync(string fcmToken, string title, string body, IReadOnlyDictionary<string, string> data, CancellationToken ct);
}

/// <summary>Meta WhatsApp Cloud API : POST {base}/{phone_number_id}/messages.</summary>
public sealed class WhatsAppCloudSender(HttpClient http, IOptions<WhatsAppSettings> options, ILogger<WhatsAppCloudSender> logger)
    : IWhatsAppSender
{
    public async Task<NotificationResult> SendAsync(string to, string message, CancellationToken ct)
    {
        var settings = options.Value;
        if (!settings.Enabled)
        {
            logger.LogInformation("[WhatsApp simulé] -> {To} : {Message}", to, message);
            return NotificationResult.Simulate();
        }

        object payload = string.IsNullOrWhiteSpace(settings.TemplateName)
            ? new { messaging_product = "whatsapp", to, type = "text", text = new { preview_url = false, body = message } }
            : new
            {
                messaging_product = "whatsapp",
                to,
                type = "template",
                template = new
                {
                    name = settings.TemplateName,
                    language = new { code = settings.TemplateLanguage },
                    // Les paramètres de modèle n'acceptent pas les retours à la ligne
                    components = new[] { new { type = "body", parameters = new[] { new { type = "text", text = message.ReplaceLineEndings(" | ") } } } }
                }
            };

        using var request = new HttpRequestMessage(HttpMethod.Post, $"{settings.ApiBaseUrl.TrimEnd('/')}/{settings.PhoneNumberId}/messages")
        {
            Content = JsonContent.Create(payload)
        };
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", settings.AccessToken);

        try
        {
            using var response = await http.SendAsync(request, ct);
            var body = await response.Content.ReadAsStringAsync(ct);
            if (!response.IsSuccessStatusCode)
            {
                logger.LogError("Échec WhatsApp vers {To} : {Status} {Body}", to, (int)response.StatusCode, body);
                return NotificationResult.Failed($"HTTP {(int)response.StatusCode}: {body}");
            }

            using var json = JsonDocument.Parse(body);
            var messageId = json.RootElement.TryGetProperty("messages", out var messages) && messages.GetArrayLength() > 0
                ? messages[0].GetProperty("id").GetString()
                : null;
            return NotificationResult.Sent(messageId);
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or JsonException)
        {
            logger.LogError(ex, "Échec WhatsApp vers {To}", to);
            return NotificationResult.Failed(ex.Message);
        }
    }
}

/// <summary>Firebase Cloud Messaging (HTTP v1 via FirebaseAdmin).</summary>
public sealed class FcmPushSender : IPushSender
{
    private readonly FirebaseMessaging? _messaging;
    private readonly ILogger<FcmPushSender> _logger;

    public FcmPushSender(IOptions<FirebaseSettings> options, ILogger<FcmPushSender> logger)
    {
        _logger = logger;
        if (!options.Value.Enabled)
            return;

        var app = FirebaseApp.DefaultInstance ?? FirebaseApp.Create(new AppOptions
        {
            Credential = GoogleCredential.FromFile(options.Value.CredentialsPath)
        });
        _messaging = FirebaseMessaging.GetMessaging(app);
    }

    public async Task<NotificationResult> SendAsync(
        string fcmToken, string title, string body, IReadOnlyDictionary<string, string> data, CancellationToken ct)
    {
        if (_messaging is null)
        {
            _logger.LogInformation("[Push simulé] {Title} : {Body}", title, body);
            return NotificationResult.Simulate();
        }

        var message = new Message
        {
            Token = fcmToken,
            Notification = new Notification { Title = title, Body = body },
            Data = data,
            Android = new AndroidConfig
            {
                Priority = Priority.High,
                Notification = new AndroidNotification { ChannelId = "health_alerts" }
            },
            Apns = new ApnsConfig { Aps = new Aps { Sound = "default" } }
        };

        try
        {
            return NotificationResult.Sent(await _messaging.SendAsync(message, ct));
        }
        catch (FirebaseMessagingException ex)
        {
            _logger.LogError(ex, "Échec push FCM ({Code})", ex.MessagingErrorCode);
            return NotificationResult.Failed($"{ex.MessagingErrorCode}: {ex.Message}");
        }
    }
}
