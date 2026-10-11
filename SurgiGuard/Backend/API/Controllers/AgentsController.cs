using API.Data;
using API.Dtos;
using API.Entites;
using API.Security;
using API.Services;
using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;

namespace API.Controllers;

/// <summary>
/// Passerelle LECTURE (+ synchro des traitements) pour le Système Multi-Agent (backend IA, dossier backend/).
/// L'API reste la source de vérité : les mesures ESP32, les traitements et les alertes sont lus ici, jamais dupliqués
/// dans une autre base. Authentification : en-tête X-Api-Key (clé « Agents »), comme /api/alerts/trigger.
/// </summary>
[ApiController]
[ServiceApiKey(ServiceClient.Agents)]
[Route("api/agents")]
[Produces("application/json")]
public sealed class AgentsController(
    MongoDbContext db,
    TelemetryService telemetry,
    MedicationService meds,
    AlertService alerts) : ControllerBase
{
    /// <summary>Patients suivis, avec le boîtier ESP32 associé (le backend IA s'en sert pour savoir quoi synchroniser).</summary>
    [HttpGet("patients")]
    public async Task<ActionResult<IReadOnlyList<AgentPatientDto>>> Patients(CancellationToken ct)
    {
        var patients = await db.Patients.Find(_ => true).ToListAsync(ct);
        var users = (await db.Users.Find(u => patients.Select(p => p.UserId).Contains(u.Id)).ToListAsync(ct))
            .ToDictionary(u => u.Id);
        var relations = await db.PatientFamilyRelations.Find(_ => true).ToListAsync(ct);
        var familyUsers = (await db.Users.Find(u => relations.Select(r => r.FamilyUserId).Contains(u.Id)).ToListAsync(ct))
            .ToDictionary(u => u.Id);

        return Ok(patients.Select(p => new AgentPatientDto(
            p.Id,
            users.TryGetValue(p.UserId, out var u) ? u.FullName : "Patient",
            p.DeviceId,
            p.DateOfBirth,
            p.MedicalFolder.Allergies,
            p.MedicalFolder.MedicalHistory,
            p.MedicalFolder.Medications,
            new ThresholdsDto { MinBpm = p.Thresholds.MinBpm, MaxBpm = p.Thresholds.MaxBpm, MinSpo2 = p.Thresholds.MinSpo2 },
            relations.Where(r => r.PatientId == p.Id).Select(r => new AgentFamilyDto(
                familyUsers.TryGetValue(r.FamilyUserId, out var f) ? f.FullName : "Proche",
                r.Relationship, r.IsPrimaryContact, r.WhatsappOptIn)).ToList())).ToList());
    }

    /// <summary>Mesures brutes strictement postérieures à <c>after</c> (ordre chronologique) : sert de curseur de synchro.</summary>
    [HttpGet("patients/{patientId}/telemetry/since")]
    public async Task<ActionResult<IReadOnlyList<TelemetryDto>>> Since(
        string patientId, [FromQuery] DateTime? after, [FromQuery] int limit = 500, CancellationToken ct = default)
    {
        if (!Ids.IsValid(patientId))
            return NotFound();

        var from = (after ?? DateTime.UtcNow.AddMinutes(-15)).ToUniversalTime();
        var rows = await db.Telemetry
            .Find(t => t.PatientId == patientId && t.Timestamp > from)
            .SortBy(t => t.Timestamp)
            .Limit(Math.Clamp(limit, 1, TelemetryService.MaxPoints))
            .ToListAsync(ct);
        return Ok(rows.Select(TelemetryDto.From).ToList());
    }

    [HttpGet("patients/{patientId}/telemetry/latest")]
    public async Task<ActionResult<TelemetryDto>> Latest(string patientId, CancellationToken ct)
    {
        if (!Ids.IsValid(patientId))
            return NotFound();
        var latest = await telemetry.GetLatestAsync(patientId, ct);
        return latest is null ? NotFound() : Ok(TelemetryDto.From(latest));
    }

    [HttpGet("patients/{patientId}/telemetry/history")]
    public async Task<ActionResult<TelemetryHistoryResponse>> History(
        string patientId, [FromQuery] DateTime? from, [FromQuery] DateTime? to,
        [FromQuery(Name = "interval_minutes")] int intervalMinutes = 1, CancellationToken ct = default)
    {
        if (!Ids.IsValid(patientId))
            return NotFound();
        var end = (to ?? DateTime.UtcNow).ToUniversalTime();
        var start = (from ?? end.AddHours(-1)).ToUniversalTime();
        var points = await telemetry.GetHistoryAsync(patientId, start, end, Math.Clamp(intervalMinutes, 0, 1440), ct);
        return Ok(new TelemetryHistoryResponse(patientId, start, end, intervalMinutes, points));
    }

    [HttpGet("patients/{patientId}/alerts")]
    public async Task<ActionResult<IReadOnlyList<AlertDto>>> Alerts(string patientId, [FromQuery] int limit = 50, CancellationToken ct = default)
    {
        if (!Ids.IsValid(patientId))
            return NotFound();
        return Ok((await alerts.GetForPatientAsync(patientId, Math.Clamp(limit, 1, 200), ct)).Select(AlertDto.From).ToList());
    }

    [HttpGet("patients/{patientId}/medications")]
    public async Task<ActionResult<IReadOnlyList<MedicationDto>>> Medications(string patientId, CancellationToken ct)
    {
        if (!Ids.IsValid(patientId))
            return NotFound();
        return Ok((await meds.ListAsync(patientId, false, ct)).Select(MedicationDto.From).ToList());
    }

    /// <summary>Prises planifiées et leur statut (mêmes règles que GET api/patients/{id}/medications/schedule).</summary>
    [HttpGet("patients/{patientId}/medications/schedule")]
    public async Task<ActionResult<IReadOnlyList<DoseDto>>> Schedule(
        string patientId, [FromQuery] string? date, [FromQuery] int days = 1, [FromQuery(Name = "as_of")] string? asOf = null, CancellationToken ct = default)
    {
        if (!Ids.IsValid(patientId))
            return NotFound();
        var from = DateOnly.FromDateTime(DateTime.UtcNow);
        if (date is not null && !MedicationService.TryParseDate(date, out from))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "date doit être au format yyyy-MM-dd.");
        if (days is < 1 or > 14 || !MedicationService.TryParseAsOf(asOf, out var now))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "days (1 à 14) ou as_of (yyyy-MM-ddTHH:mm) invalide.");
        return Ok(await meds.ScheduleAsync(patientId, from, days, now, ct));
    }

    [HttpGet("patients/{patientId}/medications/adherence")]
    public async Task<ActionResult<AdherenceReportDto>> Adherence(
        string patientId, [FromQuery] string? from, [FromQuery] string? to, [FromQuery(Name = "as_of")] string? asOf = null, CancellationToken ct = default)
    {
        if (!Ids.IsValid(patientId))
            return NotFound();
        if (!MedicationService.TryParseAsOf(asOf, out var now))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "as_of doit être au format yyyy-MM-ddTHH:mm.");
        var end = DateOnly.FromDateTime(now);
        if (to is not null && !MedicationService.TryParseDate(to, out end))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "to doit être au format yyyy-MM-dd.");
        var start = end.AddDays(-6);
        if (from is not null && !MedicationService.TryParseDate(from, out start))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "from doit être au format yyyy-MM-dd.");
        if (start > end || end.DayNumber - start.DayNumber >= MedicationService.MaxRangeDays)
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: $"Période invalide ({MedicationService.MaxRangeDays} jours maximum).");
        return Ok(await meds.AdherenceAsync(patientId, start, end, now, ct));
    }

    /// <summary>
    /// Pousse le plan de soins confirmé par le patient (backend IA) vers les traitements de l'API : un médicament est
    /// créé s'il n'existe pas encore (même nom), sinon ses heures sont mises à jour. Rien n'est jamais supprimé.
    /// Les alarmes de l'app Android et le suivi d'observance s'appuient ensuite sur ces traitements.
    /// </summary>
    [HttpPost("patients/{patientId}/medications/sync")]
    public async Task<ActionResult<MedicationSyncResult>> SyncMedications(
        string patientId, List<CreateMedicationRequest> plan, CancellationToken ct)
    {
        if (!Ids.IsValid(patientId) || !await db.Patients.Find(p => p.Id == patientId).AnyAsync(ct))
            return NotFound();

        var existing = await meds.ListAsync(patientId, false, ct);
        int created = 0, updated = 0, unchanged = 0;
        foreach (var item in plan)
        {
            if (!MedicationService.TryNormalizeTimes(item.Times, out var times))
                return Problem(statusCode: StatusCodes.Status400BadRequest, title: $"Heures invalides pour {item.Name}.");

            var current = existing.FirstOrDefault(m => string.Equals(m.Name, item.Name.Trim(), StringComparison.OrdinalIgnoreCase));
            if (current is null)
            {
                var start = MedicationService.TryParseDate(item.StartDate, out var s) ? s : DateOnly.FromDateTime(DateTime.UtcNow);
                await db.Medications.InsertOneAsync(new Medication
                {
                    PatientId = patientId,
                    Name = item.Name.Trim(),
                    Dosage = item.Dosage?.Trim(),
                    Instructions = item.Instructions?.Trim(),
                    Times = times,
                    StartDate = MedicationService.Fmt(start),
                    EndDate = MedicationService.TryParseDate(item.EndDate, out var e) ? MedicationService.Fmt(e) : null,
                    PrescribedByName = "SurgiGuard AI (plan confirmé)"
                }, cancellationToken: ct);
                created++;
            }
            else if (!current.Times.SequenceEqual(times) || current.Dosage != item.Dosage?.Trim())
            {
                current.Times = times;
                current.Dosage = item.Dosage?.Trim() ?? current.Dosage;
                await db.Medications.ReplaceOneAsync(m => m.Id == current.Id, current, cancellationToken: ct);
                updated++;
            }
            else unchanged++;
        }
        return Ok(new MedicationSyncResult(created, updated, unchanged));
    }
}

public sealed record AgentFamilyDto(string FullName, string Relationship, bool IsPrimaryContact, bool WhatsappOptIn);

public sealed record AgentPatientDto(
    string Id,
    string FullName,
    string? DeviceId,
    DateTime? DateOfBirth,
    IReadOnlyList<string> Allergies,
    IReadOnlyList<string> MedicalHistory,
    IReadOnlyList<string> Medications,
    ThresholdsDto Thresholds,
    IReadOnlyList<AgentFamilyDto> Family);

public sealed record MedicationSyncResult(int Created, int Updated, int Unchanged);
