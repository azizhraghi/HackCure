using System.Net.Http.Headers;
using API.Security;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers;

/// <summary>
/// Relais vers l'assistant IA (FastAPI + Mistral, AppMobile/backend) : l'app n'a qu'une URL (le tunnel ngrok)
/// et le proxy Mistral n'est pas exposé publiquement sans JWT.
/// </summary>
[ApiController]
[Authorize(Roles = Roles.Patient)]
[Route("chat")]
public sealed class ChatController(IHttpClientFactory httpFactory, ILogger<ChatController> logger) : ControllerBase
{
    public const string HttpClientName = "chat";

    /// <summary>Corps transmis tel quel : { "messages": [{ "role", "content" }], "lang" } → { "reply", "escalate" }.</summary>
    [HttpPost]
    [Consumes("application/json")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status502BadGateway)]
    public async Task<IActionResult> Chat(CancellationToken ct)
    {
        using var content = new StreamContent(Request.Body);
        content.Headers.ContentType = new MediaTypeHeaderValue("application/json");

        try
        {
            using var response = await httpFactory.CreateClient(HttpClientName).PostAsync("chat", content, ct);
            var body = await response.Content.ReadAsStringAsync(ct);
            return new ContentResult { StatusCode = (int)response.StatusCode, Content = body, ContentType = "application/json" };
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
        {
            logger.LogError(ex, "Assistant IA injoignable");
            return Problem(statusCode: StatusCodes.Status502BadGateway, title: "Assistant IA injoignable.");
        }
    }
}
