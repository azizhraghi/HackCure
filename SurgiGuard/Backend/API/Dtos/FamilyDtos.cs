using System.ComponentModel.DataAnnotations;

namespace API.Dtos;

public sealed record LinkPatientRequest
{
    /// <summary>Code affiché dans l'app du patient (GET /api/patients/me → link_code).</summary>
    [Required, RegularExpression(@"^\s*\d{6}\s*$", ErrorMessage = "Le code de liaison contient 6 chiffres.")]
    public string LinkCode { get; init; } = "";

    [Required, MaxLength(40)]
    public string Relationship { get; init; } = "";

    public bool WhatsappOptIn { get; init; }

    /// <summary>Si aucun proche n'est encore contact principal, le premier lié le devient automatiquement.</summary>
    public bool IsPrimaryContact { get; init; }
}

public sealed record FollowedPatientDto(
    string PatientId,
    string FullName,
    DateTime? DateOfBirth,
    string? DeviceId,
    string Relationship,
    bool IsPrimaryContact,
    bool WhatsappOptIn,
    DateTime LinkedAt,
    TelemetryDto? LatestTelemetry);
