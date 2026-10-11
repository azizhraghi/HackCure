using System.ComponentModel.DataAnnotations;
using API.Entites;

namespace API.Dtos;

public sealed record RegisterRequest
{
    [Required, EmailAddress, MaxLength(254)]
    public string Email { get; init; } = "";

    [Required, MinLength(8), MaxLength(128)]
    public string Password { get; init; } = "";

    [Required]
    public UserRole? Role { get; init; }

    [Required, MaxLength(80)]
    public string FirstName { get; init; } = "";

    [Required, MaxLength(80)]
    public string LastName { get; init; } = "";

    [Phone, MaxLength(32)]
    public string? Phone { get; init; }

    /// <summary>Si absent, le numéro de téléphone est utilisé.</summary>
    [Phone, MaxLength(32)]
    public string? WhatsappNumber { get; init; }

    [MaxLength(4096)]
    public string? FcmToken { get; init; }

    // --- PATIENT ---
    public DateTime? DateOfBirth { get; init; }

    [MaxLength(20)]
    public string? Gender { get; init; }

    [MaxLength(64)]
    public string? DeviceId { get; init; }

    // --- NURSE / DOCTOR ---
    public string? StaffCode { get; init; }
}

public sealed record LoginRequest
{
    [Required, EmailAddress]
    public string Email { get; init; } = "";

    [Required]
    public string Password { get; init; } = "";

    /// <summary>Met à jour le token push de l'appareil courant.</summary>
    [MaxLength(4096)]
    public string? FcmToken { get; init; }
}

public sealed record FcmTokenRequest
{
    [Required, MaxLength(4096)]
    public string FcmToken { get; init; } = "";
}

public sealed record UserDto(
    string Id,
    string Email,
    UserRole Role,
    string FirstName,
    string LastName,
    string? Phone,
    string? WhatsappNumber);

/// <param name="ProfileId">Id du document Patient ou FamilyMember selon le rôle (null pour le personnel soignant).</param>
public sealed record AuthResponse(
    string AccessToken,
    string TokenType,
    DateTime ExpiresAt,
    UserDto User,
    string? ProfileId);
