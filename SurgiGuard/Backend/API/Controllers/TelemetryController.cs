using API.Dtos;
using API.Security;
using API.Services;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers;

[ApiController]
[Route("api/telemetry")]
[Produces("application/json")]
public sealed class TelemetryController(TelemetryService telemetry, ILogger<TelemetryController> logger) : ControllerBase
{
    /// <summary>
    /// Reçoit une mesure de l'ESP32, relayée depuis le broker MQTT (passerelle / Node-RED), authentifiée par X-Api-Key.
    /// La réponse liste les dépassements de seuils ; la décision d'alerter reste au Système Multi-Agent (POST /api/alerts/trigger).
    /// </summary>
    [ServiceApiKey(ServiceClient.Iot)]
    [HttpPost("ingest")]
    [ProducesResponseType<TelemetryIngestResponse>(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<TelemetryIngestResponse>> Ingest(TelemetryIngestRequest request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(request.DeviceId) && string.IsNullOrWhiteSpace(request.PatientId))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "device_id ou patient_id requis.");

        var result = await telemetry.IngestAsync(request, ct);
        if (result is null)
        {
            logger.LogWarning("Télémétrie rejetée : boîtier {DeviceId} / patient {PatientId} inconnu", request.DeviceId, request.PatientId);
            return Problem(statusCode: StatusCodes.Status404NotFound, title: "Aucun patient associé à ce boîtier.");
        }

        if (result.Anomalies.Count > 0)
            logger.LogInformation("Patient {PatientId} : anomalies {Anomalies}", result.Patient.Id, string.Join(", ", result.Anomalies));

        return Accepted(new TelemetryIngestResponse(result.Patient.Id, result.Reading.Timestamp, result.Anomalies));
    }
}
