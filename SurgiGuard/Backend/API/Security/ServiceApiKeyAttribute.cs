using System.Security.Cryptography;
using System.Text;
using API.Settings;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.Extensions.Options;

namespace API.Security;

public enum ServiceClient
{
    Iot,
    Agents
}

/// <summary>Authentifie un client machine (ESP32/passerelle MQTT, agents) via l'en-tête X-Api-Key.</summary>
[AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
public sealed class ServiceApiKeyAttribute(ServiceClient client) : Attribute, IAuthorizationFilter
{
    public const string HeaderName = "X-Api-Key";

    public void OnAuthorization(AuthorizationFilterContext context)
    {
        var keys = context.HttpContext.RequestServices.GetRequiredService<IOptions<ServiceApiKeysSettings>>().Value;
        var expected = client == ServiceClient.Iot ? keys.Iot : keys.Agents;

        if (string.IsNullOrEmpty(expected))
        {
            context.Result = new ObjectResult(new ProblemDetails
            {
                Status = StatusCodes.Status503ServiceUnavailable,
                Title = $"Clé API '{client}' non configurée sur le serveur."
            }) { StatusCode = StatusCodes.Status503ServiceUnavailable };
            return;
        }

        var provided = context.HttpContext.Request.Headers[HeaderName].ToString();
        if (!CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(provided), Encoding.UTF8.GetBytes(expected)))
            context.Result = new UnauthorizedResult();
    }
}
