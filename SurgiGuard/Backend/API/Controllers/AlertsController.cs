using API.Dtos;
using API.Security;
using API.Services;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers;

[ApiController]
[Route("api/alerts")]
[Produces("application/json")]
public sealed class AlertsController(AlertService alerts) : ControllerBase
{
    /// <summary>
    /// Utilisé par le Système Multi-Agent (X-Api-Key) : enregistre l'alerte puis notifie les proches
    /// (push FCM ; WhatsApp selon la gravité et l'opt-in). La réponse contient le résultat de chaque envoi.
    /// </summary>
    [ServiceApiKey(ServiceClient.Agents)]
    [HttpPost("trigger")]
    [ProducesResponseType<AlertDto>(StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<AlertDto>> Trigger(TriggerAlertRequest request, CancellationToken ct)
    {
        var alert = await alerts.TriggerAsync(request, ct);
        if (alert is null)
            return Problem(statusCode: StatusCodes.Status404NotFound, title: "Patient introuvable.");

        return StatusCode(StatusCodes.Status201Created, AlertDto.From(alert));
    }
}
