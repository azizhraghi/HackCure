using System.Text;
using System.Text.Json;
using API.Dtos;
using API.Settings;
using Microsoft.Extensions.Options;
using MQTTnet;
using MQTTnet.Client;

namespace API.Services;

/// <summary>
/// Pont MQTT → base : s'abonne au topic de l'ESP32 (EMQX), convertit chaque message en mesure
/// et l'enregistre pour le patient dont le boîtier (device_id) correspond.
/// Champs ESP32 : temp, hum, bpm, spo2, activity, motion, device_id.
/// </summary>
public sealed class MqttBridgeService(
    IOptions<MqttSettings> options,
    IServiceScopeFactory scopes,
    ILogger<MqttBridgeService> logger) : BackgroundService
{
    private readonly MqttSettings _cfg = options.Value;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (!_cfg.Enabled)
        {
            logger.LogInformation("Pont MQTT désactivé (Mqtt:Enabled=false)");
            return;
        }

        var client = new MqttFactory().CreateMqttClient();
        client.ApplicationMessageReceivedAsync += e => HandleAsync(e, stoppingToken);

        var clientOptions = new MqttClientOptionsBuilder()
            .WithTcpServer(_cfg.Broker, _cfg.Port)
            .WithCredentials(_cfg.Username, _cfg.Password)
            .WithClientId($"surgiguard-api-{Environment.MachineName}")
            .WithTlsOptions(o => o.UseTls(_cfg.UseTls))
            .WithKeepAlivePeriod(TimeSpan.FromSeconds(30))
            .Build();

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                if (!client.IsConnected)
                {
                    await client.ConnectAsync(clientOptions, stoppingToken);
                    await client.SubscribeAsync(_cfg.Topic, cancellationToken: stoppingToken);
                    logger.LogInformation("Pont MQTT connecté à {Broker}, topic {Topic}", _cfg.Broker, _cfg.Topic);
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                logger.LogWarning("Connexion MQTT impossible ({Message}), nouvel essai dans 5 s", ex.Message);
            }

            try { await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken); }
            catch (OperationCanceledException) { break; }
        }

        if (client.IsConnected)
            await client.DisconnectAsync();
        client.Dispose();
    }

    private async Task HandleAsync(MqttApplicationMessageReceivedEventArgs e, CancellationToken ct)
    {
        try
        {
            var json = Encoding.UTF8.GetString(e.ApplicationMessage.PayloadSegment);
            var request = Parse(json);
            if (request is null)
                return;

            using var scope = scopes.CreateScope();
            var result = await scope.ServiceProvider.GetRequiredService<TelemetryService>().IngestAsync(request, ct);
            if (result is null)
                logger.LogWarning("MQTT : aucun patient pour le boîtier {DeviceId} (à enregistrer via PUT /api/patients/me/device)", request.DeviceId);
            else if (result.Anomalies.Count > 0)
                logger.LogInformation("Patient {PatientId} : anomalies {Anomalies}", result.Patient.Id, string.Join(", ", result.Anomalies));
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Message MQTT ignoré");
        }
    }

    private TelemetryIngestRequest? Parse(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        if (root.ValueKind != JsonValueKind.Object)
            return null;

        var deviceId = Str(root, "device_id") ?? _cfg.DefaultDeviceId;
        if (string.IsNullOrWhiteSpace(deviceId))
            return null;

        var bpm = Num(root, "bpm");
        var activity = Num(root, "activity");
        // Mêmes seuils que le firmware (motion.cpp) ; le libellé du message sert de repli
        var motion = activity is null ? Str(root, "motion")?.Replace(' ', '_') : activity >= 1.5 ? "AGITE" : activity >= 0.3 ? "LEGER" : "IMMOBILE";

        return new TelemetryIngestRequest
        {
            DeviceId = deviceId,
            Bpm = bpm is null ? null : (int)Math.Clamp(Math.Round(bpm.Value), 0, 300),
            Spo2 = Clamp(Num(root, "spo2"), 0, 100),
            RoomTemp = Clamp(Num(root, "temp"), -40, 85),
            RoomHumidity = Clamp(Num(root, "hum"), 0, 100),
            MotionState = motion
        };
    }

    private static double? Clamp(double? v, double min, double max) => v is null ? null : Math.Clamp(v.Value, min, max);

    private static string? Str(JsonElement o, string name) =>
        o.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;

    private static double? Num(JsonElement o, string name) =>
        o.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetDouble() : null;
}
