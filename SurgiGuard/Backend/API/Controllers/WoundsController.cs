using System.Net.Http.Headers;
using API.Data;
using API.Security;
using API.Settings;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using MongoDB.Driver;

namespace API.Controllers;

/// <summary>
/// Photos de plaie aux changements de pansement : relais vers le backend IA (analyse OpenCV + lecture par un LLM vision).
/// L'app Android n'a qu'une URL (le tunnel ngrok) ; le backend IA n'est jamais exposé sans JWT patient.
/// Seul le patient suivi par le backend IA (celui qui possède le boîtier ESP32 lié) est servi.
/// </summary>
[ApiController]
[Authorize(Roles = Roles.Patient)]
[Route("api/patients/me")]
public sealed class WoundsController(
    IHttpClientFactory httpFactory,
    MongoDbContext db,
    IOptions<ServiceApiKeysSettings> keys,
    ILogger<WoundsController> logger) : ControllerBase
{
    private async Task<string?> MyPatientIdAsync(CancellationToken ct)
    {
        var userId = User.GetUserId();
        return (await db.Patients.Find(p => p.UserId == userId).FirstOrDefaultAsync(ct))?.Id;
    }

    private HttpClient Client()
    {
        var client = httpFactory.CreateClient(ChatController.HttpClientName);
        client.DefaultRequestHeaders.Remove(ServiceApiKeyAttribute.HeaderName);
        client.DefaultRequestHeaders.Add(ServiceApiKeyAttribute.HeaderName, keys.Value.Agents);
        return client;
    }

    private static ContentResult Relay(HttpResponseMessage r, string body) =>
        new() { StatusCode = (int)r.StatusCode, Content = body, ContentType = "application/json" };

    /// <summary>Photo due maintenant ? (fenêtres de pansement du plan de soins) et dernières photos analysées.</summary>
    [HttpGet("wound")]
    public async Task<IActionResult> Get(CancellationToken ct)
    {
        var pid = await MyPatientIdAsync(ct);
        if (pid is null) return NotFound();
        try
        {
            using var r = await Client().GetAsync($"hub/wound/{pid}", ct);
            return Relay(r, await r.Content.ReadAsStringAsync(ct));
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
        {
            logger.LogError(ex, "Backend IA injoignable (plaie)");
            return Problem(statusCode: StatusCodes.Status502BadGateway, title: "Backend IA injoignable.");
        }
    }

    /// <summary>multipart/form-data : file (image), dressing_change_confirmed (true/false).</summary>
    [HttpPost("wound-photos")]
    [RequestSizeLimit(13_000_000)]
    public async Task<IActionResult> Upload(IFormFile file, [FromForm(Name = "dressing_change_confirmed")] bool confirmed, CancellationToken ct)
    {
        var pid = await MyPatientIdAsync(ct);
        if (pid is null) return NotFound();
        using var form = new MultipartFormDataContent();
        var content = new StreamContent(file.OpenReadStream());
        content.Headers.ContentType = new MediaTypeHeaderValue(string.IsNullOrEmpty(file.ContentType) ? "image/jpeg" : file.ContentType);
        form.Add(content, "file", string.IsNullOrEmpty(file.FileName) ? "wound.jpg" : file.FileName);
        form.Add(new StringContent(confirmed ? "true" : "false"), "dressing_change_confirmed");
        try
        {
            using var r = await Client().PostAsync($"hub/wound/{pid}", form, ct);
            return Relay(r, await r.Content.ReadAsStringAsync(ct));
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
        {
            logger.LogError(ex, "Backend IA injoignable (photo de plaie)");
            return Problem(statusCode: StatusCodes.Status502BadGateway, title: "Backend IA injoignable.");
        }
    }

    /// <summary>Image (photo ou contour calculé) : path = « uploads/xxx.jpg » ou « static/photos/day1.jpg ».</summary>
    [HttpGet("wound-media")]
    public async Task<IActionResult> Media([FromQuery] string path, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(path) || path.Contains("..") ||
            !(path.StartsWith("/uploads/") || path.StartsWith("/static/photos/")))
            return BadRequest();
        try
        {
            using var r = await Client().GetAsync(path.TrimStart('/'), ct);
            if (!r.IsSuccessStatusCode) return StatusCode((int)r.StatusCode);
            return File(await r.Content.ReadAsByteArrayAsync(ct), r.Content.Headers.ContentType?.ToString() ?? "image/jpeg");
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
        {
            logger.LogError(ex, "Backend IA injoignable (image)");
            return Problem(statusCode: StatusCodes.Status502BadGateway, title: "Backend IA injoignable.");
        }
    }
}
