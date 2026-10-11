using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Mvc;

namespace API.Dtos;

public sealed record PatientProfileDto(
    string Id,
    UserDto User,
    DateTime? DateOfBirth,
    string? Gender,
    string? Address,
    string? DeviceId,
    string LinkCode,
    MedicalFolderDto MedicalFolder,
    ThresholdsDto Thresholds,
    IReadOnlyList<LinkedFamilyMemberDto> FamilyMembers);

public sealed record MedicalFolderDto(
    string? BloodType,
    IReadOnlyList<string> Allergies,
    IReadOnlyList<string> MedicalHistory,
    IReadOnlyList<string> Medications,
    string? Notes,
    IReadOnlyList<MedicalDocumentDto> Documents,
    DateTime? UpdatedAt);

/// <param name="Url">URL relative, à appeler avec le JWT (GET).</param>
public sealed record MedicalDocumentDto(string Id, string FileName, long SizeBytes, string Url, DateTime UploadedAt);

public sealed record LinkedFamilyMemberDto(
    string FamilyMemberId,
    string FullName,
    string? Phone,
    string Relationship,
    bool IsPrimaryContact,
    bool WhatsappOptIn);

public sealed record ThresholdsDto
{
    [Range(20, 250)]
    public int MinBpm { get; init; }

    [Range(20, 250)]
    public int MaxBpm { get; init; }

    [Range(50, 100)]
    public double MinSpo2 { get; init; }
}

public sealed record UpdateDeviceRequest
{
    [Required, MaxLength(64)]
    public string DeviceId { get; init; } = "";
}

/// <summary>
/// multipart/form-data. Les champs texte REMPLACENT le dossier existant (envoyer le dossier complet).
/// Les PDF de <c>documents</c> sont AJOUTÉS ; <c>remove_document_ids</c> supprime des PDF existants.
/// </summary>
public sealed class MedicalFolderUpdateForm
{
    [FromForm(Name = "blood_type"), RegularExpression("^(A|B|AB|O)[+-]$", ErrorMessage = "Groupe sanguin invalide (ex : O+, AB-).")]
    public string? BloodType { get; set; }

    [FromForm(Name = "allergies")]
    public List<string> Allergies { get; set; } = [];

    [FromForm(Name = "medical_history")]
    public List<string> MedicalHistory { get; set; } = [];

    [FromForm(Name = "medications")]
    public List<string> Medications { get; set; } = [];

    [FromForm(Name = "notes"), MaxLength(4000)]
    public string? Notes { get; set; }

    [FromForm(Name = "documents")]
    public List<IFormFile> Documents { get; set; } = [];

    [FromForm(Name = "remove_document_ids")]
    public List<string> RemoveDocumentIds { get; set; } = [];
}
