using API.Data;
using API.Dtos;
using API.Entites;
using API.Security;
using API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;

namespace API.Controllers;

[ApiController]
[Authorize]
[Route("api/patients")]
[Produces("application/json")]
public sealed class PatientsController(
    MongoDbContext db,
    PatientAccessService access,
    TelemetryService telemetry,
    AlertService alerts,
    MedicalFolderService folders) : ControllerBase
{
    private const int MaxHistoryDays = 31;

    /// <summary>Profil complet du patient connecté (dossier médical, seuils, code de liaison, proches).</summary>
    [Authorize(Roles = Roles.Patient)]
    [HttpGet("me")]
    [ProducesResponseType<PatientProfileDto>(StatusCodes.Status200OK)]
    public async Task<ActionResult<PatientProfileDto>> GetMe(CancellationToken ct)
    {
        var patient = await GetCurrentPatientAsync(ct);
        if (patient is null)
            return NotFound();

        var user = await db.Users.Find(u => u.Id == patient.UserId).FirstAsync(ct);
        var relations = await db.PatientFamilyRelations.Find(r => r.PatientId == patient.Id).ToListAsync(ct);
        var familyUserIds = relations.Select(r => r.FamilyUserId).ToList();
        var familyUsers = (await db.Users.Find(Builders<User>.Filter.In(u => u.Id, familyUserIds)).ToListAsync(ct))
            .ToDictionary(u => u.Id);

        var family = relations
            .Where(r => familyUsers.ContainsKey(r.FamilyUserId))
            .Select(r => new LinkedFamilyMemberDto(
                r.FamilyMemberId,
                familyUsers[r.FamilyUserId].FullName,
                familyUsers[r.FamilyUserId].Phone,
                r.Relationship,
                r.IsPrimaryContact,
                r.WhatsappOptIn))
            .ToList();

        return Ok(new PatientProfileDto(
            patient.Id,
            user.ToDto(),
            patient.DateOfBirth,
            patient.Gender,
            patient.Address,
            patient.DeviceId,
            patient.LinkCode,
            patient.MedicalFolder.ToDto(patient.Id),
            patient.Thresholds.ToDto(),
            family));
    }

    /// <summary>
    /// Met à jour le dossier médical (multipart/form-data). Listes : clés répétées (allergies=a&amp;allergies=b)
    /// ou indexées (allergies[0]=a). PDF : champ "documents", 10 Mo max chacun.
    /// </summary>
    [Authorize(Roles = Roles.Patient)]
    [HttpPut("me/medical-folder")]
    [Consumes("multipart/form-data")]
    [RequestSizeLimit(60 * 1024 * 1024)]
    [RequestFormLimits(MultipartBodyLengthLimit = 60 * 1024 * 1024)]
    [ProducesResponseType<MedicalFolderDto>(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<MedicalFolderDto>> UpdateMedicalFolder([FromForm] MedicalFolderUpdateForm form, CancellationToken ct)
    {
        var patient = await GetCurrentPatientAsync(ct);
        if (patient is null)
            return NotFound();

        var error = MedicalFolderService.Validate(form, patient.MedicalFolder);
        if (error is not null)
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: error);

        var folder = await folders.UpdateAsync(patient, form, ct);
        return Ok(folder.ToDto(patient.Id));
    }

    /// <summary>Associe (ou remplace) le boîtier ESP32 du patient connecté.</summary>
    [Authorize(Roles = Roles.Patient)]
    [HttpPut("me/device")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> UpdateDevice(UpdateDeviceRequest request, CancellationToken ct)
    {
        var patient = await GetCurrentPatientAsync(ct);
        if (patient is null)
            return NotFound();

        var deviceId = request.DeviceId.Trim();
        if (await db.Patients.Find(p => p.DeviceId == deviceId && p.Id != patient.Id).AnyAsync(ct))
            return Problem(statusCode: StatusCodes.Status409Conflict, title: "Ce boîtier est déjà associé à un autre patient.");

        await db.Patients.UpdateOneAsync(p => p.Id == patient.Id, Builders<Patient>.Update.Set(p => p.DeviceId, deviceId), cancellationToken: ct);
        return NoContent();
    }

    /// <summary>Seuils personnalisés (patient lui-même ou personnel soignant).</summary>
    [Authorize(Roles = $"{Roles.Patient},{Roles.Doctor},{Roles.Nurse}")]
    [HttpPut("{id}/thresholds")]
    [ProducesResponseType<ThresholdsDto>(StatusCodes.Status200OK)]
    public async Task<ActionResult<ThresholdsDto>> UpdateThresholds(string id, ThresholdsDto request, CancellationToken ct)
    {
        if (!await access.CanAccessAsync(User, id, ct))
            return NotFound();
        if (request.MinBpm >= request.MaxBpm)
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "min_bpm doit être inférieur à max_bpm.");

        var thresholds = new VitalThresholds { MinBpm = request.MinBpm, MaxBpm = request.MaxBpm, MinSpo2 = request.MinSpo2 };
        await db.Patients.UpdateOneAsync(p => p.Id == id, Builders<Patient>.Update.Set(p => p.Thresholds, thresholds), cancellationToken: ct);
        return Ok(thresholds.ToDto());
    }

    /// <summary>Dernière mesure reçue des capteurs.</summary>
    [HttpGet("{id}/telemetry/latest")]
    [ProducesResponseType<TelemetryDto>(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<ActionResult<TelemetryDto>> GetLatestTelemetry(string id, CancellationToken ct)
    {
        if (!await access.CanAccessAsync(User, id, ct))
            return NotFound();

        var latest = await telemetry.GetLatestAsync(id, ct);
        return latest is null ? NoContent() : Ok(TelemetryDto.From(latest));
    }

    /// <summary>
    /// Historique pour les graphiques. Par défaut : dernières 24 h, moyennes sur 5 min.
    /// interval_minutes = 0 renvoie les mesures brutes (2000 plus récentes max).
    /// </summary>
    [HttpGet("{id}/telemetry/history")]
    [ProducesResponseType<TelemetryHistoryResponse>(StatusCodes.Status200OK)]
    public async Task<ActionResult<TelemetryHistoryResponse>> GetTelemetryHistory(
        string id,
        [FromQuery] DateTime? from,
        [FromQuery] DateTime? to,
        [FromQuery(Name = "interval_minutes")] int intervalMinutes = 5,
        CancellationToken ct = default)
    {
        if (!await access.CanAccessAsync(User, id, ct))
            return NotFound();

        var end = to?.ToUniversalTime() ?? DateTime.UtcNow;
        var start = from?.ToUniversalTime() ?? end.AddHours(-24);
        if (start >= end || end - start > TimeSpan.FromDays(MaxHistoryDays))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: $"Période invalide ({MaxHistoryDays} jours maximum).");
        if (intervalMinutes is < 0 or > 1440)
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "interval_minutes doit être compris entre 0 et 1440.");
        if (intervalMinutes > 0 && (end - start).TotalMinutes / intervalMinutes > TelemetryService.MaxPoints)
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: $"Trop de points : augmentez interval_minutes ({TelemetryService.MaxPoints} points max).");

        var points = await telemetry.GetHistoryAsync(id, start, end, intervalMinutes, ct);
        return Ok(new TelemetryHistoryResponse(id, start, end, intervalMinutes, points));
    }

    /// <summary>Historique des alertes du patient (plus récentes d'abord).</summary>
    [HttpGet("{id}/alerts")]
    [ProducesResponseType<IReadOnlyList<AlertDto>>(StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<AlertDto>>> GetAlerts(string id, [FromQuery] int limit = 50, CancellationToken ct = default)
    {
        if (!await access.CanAccessAsync(User, id, ct))
            return NotFound();

        var list = await alerts.GetForPatientAsync(id, Math.Clamp(limit, 1, 200), ct);
        return Ok(list.Select(AlertDto.From).ToList());
    }

    /// <summary>Télécharge un PDF du dossier médical.</summary>
    [HttpGet("{id}/documents/{documentId}")]
    [Produces("application/pdf")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public async Task<IActionResult> GetDocument(string id, string documentId, CancellationToken ct)
    {
        if (!await access.CanAccessAsync(User, id, ct))
            return NotFound();

        var patient = await db.Patients.Find(p => p.Id == id).FirstOrDefaultAsync(ct);
        var opened = patient is null ? null : await folders.OpenAsync(patient, documentId, ct);
        if (opened is null)
            return NotFound();

        return File(opened.Value.Content, "application/pdf", opened.Value.Document.FileName);
    }

    private Task<Patient?> GetCurrentPatientAsync(CancellationToken ct)
    {
        var userId = User.GetUserId();
        return db.Patients.Find(p => p.UserId == userId).FirstOrDefaultAsync(ct)!;
    }
}
