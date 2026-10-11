using System.Security.Claims;
using API.Entites;

namespace API.Security;

/// <summary>Noms des rôles tels qu'ils apparaissent dans le JWT et dans [Authorize(Roles = ...)].</summary>
public static class Roles
{
    public const string Patient = "PATIENT";
    public const string FamilyMember = "FAMILY_MEMBER";
    public const string Nurse = "NURSE";
    public const string Doctor = "DOCTOR";

    public const string ClaimType = "role";
    public const string UserIdClaimType = "sub";

    public static string ToClaim(this UserRole role) => role switch
    {
        UserRole.Patient => Patient,
        UserRole.FamilyMember => FamilyMember,
        UserRole.Nurse => Nurse,
        UserRole.Doctor => Doctor,
        _ => throw new ArgumentOutOfRangeException(nameof(role))
    };

    public static UserRole? FromClaim(string? value) => value switch
    {
        Patient => UserRole.Patient,
        FamilyMember => UserRole.FamilyMember,
        Nurse => UserRole.Nurse,
        Doctor => UserRole.Doctor,
        _ => null
    };

    public static string GetUserId(this ClaimsPrincipal principal) =>
        principal.FindFirstValue(UserIdClaimType) ?? throw new InvalidOperationException("Token sans claim 'sub'.");

    public static UserRole? GetRole(this ClaimsPrincipal principal) => FromClaim(principal.FindFirstValue(ClaimType));
}
