using System.Security.Claims;
using System.Text;
using API.Entites;
using API.Settings;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;

namespace API.Security;

public sealed class TokenService(IOptions<JwtSettings> options)
{
    private readonly JsonWebTokenHandler _handler = new();

    public (string Token, DateTime ExpiresAt) CreateToken(User user)
    {
        var settings = options.Value;
        var expiresAt = DateTime.UtcNow.AddMinutes(settings.ExpiryMinutes);

        var descriptor = new SecurityTokenDescriptor
        {
            Issuer = settings.Issuer,
            Audience = settings.Audience,
            Expires = expiresAt,
            Subject = new ClaimsIdentity(
            [
                new Claim(Roles.UserIdClaimType, user.Id),
                new Claim("email", user.Email),
                new Claim(Roles.ClaimType, user.Role.ToClaim())
            ]),
            SigningCredentials = new SigningCredentials(
                new SymmetricSecurityKey(Encoding.UTF8.GetBytes(settings.Key)), SecurityAlgorithms.HmacSha256)
        };

        return (_handler.CreateToken(descriptor), expiresAt);
    }
}
