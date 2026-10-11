using System.Security.Cryptography;
using API.Data;
using API.Dtos;
using API.Entites;
using API.Security;
using API.Settings;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using MongoDB.Driver;

namespace API.Controllers;

[ApiController]
[Route("api/auth")]
[Produces("application/json")]
public sealed class AuthController(MongoDbContext db, TokenService tokens, IOptions<AuthSettings> authSettings) : ControllerBase
{
    // Code à 6 chiffres : saisi sur le pavé numérique ou scanné en QR par l'app famille
    private const string LinkCodeAlphabet = "0123456789";
    private const int LinkCodeLength = 6;

    /// <summary>Crée un compte et son profil (Patient ou FamilyMember) puis renvoie un JWT.</summary>
    [HttpPost("register")]
    [ProducesResponseType<AuthResponse>(StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<ActionResult<AuthResponse>> Register(RegisterRequest request, CancellationToken ct)
    {
        var role = request.Role!.Value;
        if (role is UserRole.Doctor or UserRole.Nurse)
        {
            var expected = authSettings.Value.StaffRegistrationCode;
            if (string.IsNullOrEmpty(expected) || request.StaffCode != expected)
                return Problem(statusCode: StatusCodes.Status403Forbidden, title: "Code d'inscription du personnel invalide.");
        }

        var email = request.Email.Trim().ToLowerInvariant();
        if (await db.Users.Find(u => u.Email == email).AnyAsync(ct))
            return Problem(statusCode: StatusCodes.Status409Conflict, title: "Cet email est déjà utilisé.");

        var deviceId = string.IsNullOrWhiteSpace(request.DeviceId) ? null : request.DeviceId.Trim();
        if (role == UserRole.Patient && deviceId is not null && await db.Patients.Find(p => p.DeviceId == deviceId).AnyAsync(ct))
            return Problem(statusCode: StatusCodes.Status409Conflict, title: "Ce boîtier est déjà associé à un patient.");

        var user = new User
        {
            Email = email,
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.Password),
            Role = role,
            FirstName = request.FirstName.Trim(),
            LastName = request.LastName.Trim(),
            Phone = request.Phone?.Trim(),
            WhatsappNumber = NormalizePhone(request.WhatsappNumber ?? request.Phone),
            FcmToken = request.FcmToken
        };

        try
        {
            await db.Users.InsertOneAsync(user, cancellationToken: ct);
        }
        catch (MongoWriteException ex) when (ex.WriteError.Category == ServerErrorCategory.DuplicateKey)
        {
            return Problem(statusCode: StatusCodes.Status409Conflict, title: "Cet email est déjà utilisé.");
        }

        string? profileId;
        try
        {
            profileId = role switch
            {
                UserRole.Patient => await CreatePatientAsync(user, request, deviceId, ct),
                UserRole.FamilyMember => await CreateFamilyMemberAsync(user, ct),
                _ => null
            };
        }
        catch
        {
            // Pas de transaction sur un Mongo standalone : on annule à la main
            await db.Users.DeleteOneAsync(u => u.Id == user.Id, CancellationToken.None);
            throw;
        }

        return StatusCode(StatusCodes.Status201Created, BuildResponse(user, profileId));
    }

    [HttpPost("login")]
    [ProducesResponseType<AuthResponse>(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<ActionResult<AuthResponse>> Login(LoginRequest request, CancellationToken ct)
    {
        var email = request.Email.Trim().ToLowerInvariant();
        var user = await db.Users.Find(u => u.Email == email).FirstOrDefaultAsync(ct);
        if (user is null || !BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            return Problem(statusCode: StatusCodes.Status401Unauthorized, title: "Email ou mot de passe incorrect.");

        if (!string.IsNullOrWhiteSpace(request.FcmToken) && request.FcmToken != user.FcmToken)
        {
            user.FcmToken = request.FcmToken;
            await db.Users.UpdateOneAsync(u => u.Id == user.Id, Builders<User>.Update.Set(u => u.FcmToken, user.FcmToken), cancellationToken: ct);
        }

        var profileId = user.Role switch
        {
            UserRole.Patient => (await db.Patients.Find(p => p.UserId == user.Id).FirstOrDefaultAsync(ct))?.Id,
            UserRole.FamilyMember => (await db.FamilyMembers.Find(f => f.UserId == user.Id).FirstOrDefaultAsync(ct))?.Id,
            _ => null
        };

        return Ok(BuildResponse(user, profileId));
    }

    /// <summary>Mise à jour du token push (appelé par l'app quand Firebase le renouvelle).</summary>
    [Authorize]
    [HttpPut("fcm-token")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> UpdateFcmToken(FcmTokenRequest request, CancellationToken ct)
    {
        var userId = User.GetUserId();
        await db.Users.UpdateOneAsync(u => u.Id == userId, Builders<User>.Update.Set(u => u.FcmToken, request.FcmToken), cancellationToken: ct);
        return NoContent();
    }

    [Authorize]
    [HttpGet("me")]
    public async Task<IActionResult> Me(CancellationToken ct)
    {
        var userId = User.GetUserId();
        var user = await db.Users.Find(u => u.Id == userId).FirstOrDefaultAsync(ct);
        if (user is null) return Unauthorized();
        string? profileId = null;
        if (user.Role == UserRole.Patient)
            profileId = (await db.Patients.Find(p => p.UserId == userId).FirstOrDefaultAsync(ct))?.Id;
        else if (user.Role == UserRole.FamilyMember)
            profileId = (await db.FamilyMembers.Find(p => p.UserId == userId).FirstOrDefaultAsync(ct))?.Id;
        return Ok(new { user = user.ToDto(), profile_id = profileId });
    }

    private AuthResponse BuildResponse(User user, string? profileId)
    {
        var (token, expiresAt) = tokens.CreateToken(user);
        return new AuthResponse(token, "Bearer", expiresAt, user.ToDto(), profileId);
    }

    private async Task<string> CreatePatientAsync(User user, RegisterRequest request, string? deviceId, CancellationToken ct)
    {
        var patient = new Patient
        {
            UserId = user.Id,
            DateOfBirth = request.DateOfBirth,
            Gender = request.Gender,
            DeviceId = deviceId
        };

        // Le code est aléatoire : en cas de collision sur l'index unique, on en tire un autre
        for (var attempt = 1; ; attempt++)
        {
            patient.LinkCode = RandomNumberGenerator.GetString(LinkCodeAlphabet, LinkCodeLength);
            try
            {
                await db.Patients.InsertOneAsync(patient, cancellationToken: ct);
                return patient.Id;
            }
            catch (MongoWriteException ex) when (ex.WriteError.Category == ServerErrorCategory.DuplicateKey
                                                 && ex.WriteError.Message.Contains("linkCode") && attempt < 10)
            {
            }
        }
    }

    private async Task<string> CreateFamilyMemberAsync(User user, CancellationToken ct)
    {
        var member = new FamilyMember { UserId = user.Id };
        await db.FamilyMembers.InsertOneAsync(member, cancellationToken: ct);
        return member.Id;
    }

    /// <summary>"+216 22 333 444" / "0021622333444" → "21622333444" (format WhatsApp Cloud API).</summary>
    private static string? NormalizePhone(string? phone)
    {
        if (string.IsNullOrWhiteSpace(phone))
            return null;
        var digits = new string(phone.Where(char.IsAsciiDigit).ToArray());
        if (digits.StartsWith("00"))
            digits = digits[2..];
        return digits.Length >= 8 ? digits : null;
    }
}
