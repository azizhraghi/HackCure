using System.ComponentModel.DataAnnotations;
using API.Entites;

namespace API.Dtos;

/// <summary>Prescription ajoutée par le médecin. times : heures locales « HH:mm » (ex. ["08:00","20:00"]).</summary>
public sealed record CreateMedicationRequest
{
    [Required, MaxLength(120)]
    public string Name { get; init; } = null!;

    [MaxLength(80)]
    public string? Dosage { get; init; }

    [MaxLength(400)]
    public string? Instructions { get; init; }

    [Required, MinLength(1), MaxLength(12)]
    public List<string> Times { get; init; } = [];

    /// <summary>« yyyy-MM-dd », défaut : aujourd'hui (UTC).</summary>
    public string? StartDate { get; init; }

    /// <summary>« yyyy-MM-dd », dernier jour inclus ; vide = sans limite.</summary>
    public string? EndDate { get; init; }
}

/// <summary>Modification partielle : seuls les champs fournis changent.</summary>
public sealed record UpdateMedicationRequest
{
    [MaxLength(120)]
    public string? Name { get; init; }

    [MaxLength(80)]
    public string? Dosage { get; init; }

    [MaxLength(400)]
    public string? Instructions { get; init; }

    [MaxLength(12)]
    public List<string>? Times { get; init; }

    public string? StartDate { get; init; }
    public string? EndDate { get; init; }
}

public sealed record MedicationDto(
    string Id,
    string PatientId,
    string Name,
    string? Dosage,
    string? Instructions,
    IReadOnlyList<string> Times,
    string StartDate,
    string? EndDate,
    bool Active,
    string PrescribedBy,
    DateTime CreatedAt)
{
    public static MedicationDto From(Medication m) =>
        new(m.Id, m.PatientId, m.Name, m.Dosage, m.Instructions, m.Times, m.StartDate, m.EndDate, m.Active, m.PrescribedByName, m.CreatedAt);
}

/// <summary>Une prise planifiée (médicament + jour + heure) avec son statut.</summary>
public sealed record DoseDto(
    string MedicationId,
    string Name,
    string? Dosage,
    string? Instructions,
    string Date,
    string Time,
    DoseStatus Status,
    DateTime? RecordedAt);

/// <summary>Le patient répond pour une prise. status absent/null = annuler sa réponse.</summary>
public sealed record RecordIntakeRequest
{
    [Required]
    public string Date { get; init; } = null!;

    [Required]
    public string Time { get; init; } = null!;

    public IntakeStatus? Status { get; init; }
}

public sealed record AdherenceCounts(int Scheduled, int Taken, int Skipped, int Missed, int Pending, double? AdherencePercent);

public sealed record MedicationAdherenceDto(string MedicationId, string Name, AdherenceCounts Counts);

public sealed record DayAdherenceDto(string Date, AdherenceCounts Counts);

/// <summary>Avancement des prises sur une période (pour le médecin, le patient et les proches).</summary>
public sealed record AdherenceReportDto(
    string PatientId,
    string From,
    string To,
    string AsOf,
    AdherenceCounts Overall,
    IReadOnlyList<MedicationAdherenceDto> Medications,
    IReadOnlyList<DayAdherenceDto> Days);
