using System.ComponentModel.DataAnnotations;
using API.Entites;

namespace API.Dtos;

public sealed record TriggerAlertRequest
{
    [Required]
    public string PatientId { get; init; } = "";

    [Required]
    public AlertType? Type { get; init; }

    /// <summary>1 = push seul, 2 = push + WhatsApp au contact principal, 3 = push + WhatsApp à tous les proches opt-in.</summary>
    [Range(1, 3)]
    public int Severity { get; init; }

    [Required, MaxLength(1000)]
    public string Message { get; init; } = "";

    /// <summary>Nom de l'agent émetteur.</summary>
    [MaxLength(100)]
    public string? Source { get; init; }

    public VitalsSnapshot? Vitals { get; init; }
}

public sealed record AlertDto(
    string Id,
    string PatientId,
    AlertType Type,
    int Severity,
    string Message,
    string? Source,
    VitalsSnapshot? Vitals,
    AlertStatus Status,
    DateTime CreatedAt,
    IReadOnlyList<NotificationRecord> Notifications)
{
    public static AlertDto From(AlertLog a) =>
        new(a.Id, a.PatientId, a.Type, a.Severity, a.Message, a.Source, a.Vitals, a.Status, a.CreatedAt, a.Notifications);
}
