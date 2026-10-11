using API.Data;
using API.Dtos;
using API.Entites;
using API.Security;
using API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;

namespace API.Controllers;

/// <summary>
/// Traitements : le personnel soignant prescrit (nom, dosage, heures), le patient consulte et répond à chaque prise,
/// le médecin, le patient et les proches consultent l'avancement. Heures et dates sont locales au patient.
/// </summary>
[ApiController]
[Authorize]
[Route("api/patients/{patientId}/medications")]
[Produces("application/json")]
public sealed class MedicationsController(MongoDbContext db, PatientAccessService access, MedicationService meds) : ControllerBase
{
    private const string Staff = $"{Roles.Doctor},{Roles.Nurse}";

    /// <summary>Traitements en cours du patient (include_stopped=true pour voir aussi les traitements arrêtés).</summary>
    [HttpGet]
    [ProducesResponseType<IReadOnlyList<MedicationDto>>(StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<MedicationDto>>> List(string patientId, [FromQuery(Name = "include_stopped")] bool includeStopped = false, CancellationToken ct = default)
    {
        if (!await access.CanAccessAsync(User, patientId, ct))
            return NotFound();

        return Ok((await meds.ListAsync(patientId, includeStopped, ct)).Select(MedicationDto.From).ToList());
    }

    /// <summary>Prescrit un médicament (médecin / infirmier) avec ses heures de prise quotidiennes.</summary>
    [Authorize(Roles = Staff)]
    [HttpPost]
    [ProducesResponseType<MedicationDto>(StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<MedicationDto>> Create(string patientId, CreateMedicationRequest request, CancellationToken ct)
    {
        if (!await access.CanAccessAsync(User, patientId, ct))
            return NotFound();
        if (!MedicationService.TryNormalizeTimes(request.Times, out var times))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "times doit contenir des heures « HH:mm » valides (ex. 08:00).");

        var start = DateOnly.FromDateTime(DateTime.UtcNow);
        if (request.StartDate is not null && !MedicationService.TryParseDate(request.StartDate, out start))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "start_date doit être au format yyyy-MM-dd.");

        string? end = null;
        if (!string.IsNullOrWhiteSpace(request.EndDate))
        {
            if (!MedicationService.TryParseDate(request.EndDate, out var endDate) || endDate < start)
                return Problem(statusCode: StatusCodes.Status400BadRequest, title: "end_date doit être au format yyyy-MM-dd et postérieure à start_date.");
            end = MedicationService.Fmt(endDate);
        }

        var userId = User.GetUserId();
        var author = await db.Users.Find(u => u.Id == userId).FirstOrDefaultAsync(ct);
        var medication = new Medication
        {
            PatientId = patientId,
            Name = request.Name.Trim(),
            Dosage = request.Dosage?.Trim(),
            Instructions = request.Instructions?.Trim(),
            Times = times,
            StartDate = MedicationService.Fmt(start),
            EndDate = end,
            PrescribedByUserId = userId,
            PrescribedByName = author?.FullName ?? "Équipe soignante"
        };
        await db.Medications.InsertOneAsync(medication, cancellationToken: ct);
        return CreatedAtAction(nameof(List), new { patientId }, MedicationDto.From(medication));
    }

    /// <summary>Modifie un traitement (nom, dosage, instructions, heures, dates).</summary>
    [Authorize(Roles = Staff)]
    [HttpPut("{medicationId}")]
    [ProducesResponseType<MedicationDto>(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<MedicationDto>> Update(string patientId, string medicationId, UpdateMedicationRequest request, CancellationToken ct)
    {
        var med = await FindAsync(patientId, medicationId, ct);
        if (med is null)
            return NotFound();

        if (!string.IsNullOrWhiteSpace(request.Name)) med.Name = request.Name.Trim();
        if (request.Dosage is not null) med.Dosage = request.Dosage.Trim();
        if (request.Instructions is not null) med.Instructions = request.Instructions.Trim();
        if (request.Times is not null)
        {
            if (!MedicationService.TryNormalizeTimes(request.Times, out var times))
                return Problem(statusCode: StatusCodes.Status400BadRequest, title: "times doit contenir des heures « HH:mm » valides.");
            med.Times = times;
        }
        if (request.StartDate is not null)
        {
            if (!MedicationService.TryParseDate(request.StartDate, out var s))
                return Problem(statusCode: StatusCodes.Status400BadRequest, title: "start_date doit être au format yyyy-MM-dd.");
            med.StartDate = MedicationService.Fmt(s);
        }
        if (request.EndDate is not null)
        {
            if (request.EndDate.Length == 0) med.EndDate = null;
            else if (MedicationService.TryParseDate(request.EndDate, out var e)) med.EndDate = MedicationService.Fmt(e);
            else return Problem(statusCode: StatusCodes.Status400BadRequest, title: "end_date doit être au format yyyy-MM-dd.");
        }

        await db.Medications.ReplaceOneAsync(m => m.Id == med.Id, med, cancellationToken: ct);
        return Ok(MedicationDto.From(med));
    }

    /// <summary>Arrête un traitement : plus de prises à partir d'aujourd'hui, l'historique est conservé.</summary>
    [Authorize(Roles = Staff)]
    [HttpDelete("{medicationId}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Stop(string patientId, string medicationId, CancellationToken ct)
    {
        var med = await FindAsync(patientId, medicationId, ct);
        if (med is null)
            return NotFound();

        var yesterday = DateOnly.FromDateTime(DateTime.UtcNow).AddDays(-1);
        if (!MedicationService.TryParseDate(med.EndDate, out var end) || end > yesterday)
            med.EndDate = MedicationService.Fmt(yesterday);
        med.Active = false;
        await db.Medications.ReplaceOneAsync(m => m.Id == med.Id, med, cancellationToken: ct);
        return NoContent();
    }

    /// <summary>
    /// Prises planifiées avec leur statut (PENDING / TAKEN / SKIPPED / MISSED) : date = jour local (défaut : aujourd'hui UTC),
    /// days = nombre de jours (1 à 14), as_of = heure locale actuelle du patient « yyyy-MM-ddTHH:mm » (défaut : heure serveur UTC).
    /// </summary>
    [HttpGet("schedule")]
    [ProducesResponseType<IReadOnlyList<DoseDto>>(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<IReadOnlyList<DoseDto>>> Schedule(
        string patientId, [FromQuery] string? date, [FromQuery] int days = 1, [FromQuery(Name = "as_of")] string? asOf = null, CancellationToken ct = default)
    {
        if (!await access.CanAccessAsync(User, patientId, ct))
            return NotFound();

        var from = DateOnly.FromDateTime(DateTime.UtcNow);
        if (date is not null && !MedicationService.TryParseDate(date, out from))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "date doit être au format yyyy-MM-dd.");
        if (days is < 1 or > 14)
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "days doit être compris entre 1 et 14.");
        if (!MedicationService.TryParseAsOf(asOf, out var now))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "as_of doit être au format yyyy-MM-ddTHH:mm.");

        return Ok(await meds.ScheduleAsync(patientId, from, days, now, ct));
    }

    /// <summary>Le patient marque une prise comme prise (TAKEN) ou ignorée (SKIPPED) ; sans status, sa réponse est annulée.</summary>
    [Authorize(Roles = Roles.Patient)]
    [HttpPut("{medicationId}/intakes")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Record(string patientId, string medicationId, RecordIntakeRequest request, CancellationToken ct)
    {
        if (!await access.CanAccessAsync(User, patientId, ct))
            return NotFound();
        var med = await FindAsync(patientId, medicationId, ct);
        if (med is null)
            return NotFound();

        if (!MedicationService.TryParseDate(request.Date, out _) || !med.Times.Contains(request.Time))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "date (yyyy-MM-dd) et time (HH:mm) doivent correspondre à une prise planifiée de ce traitement.");

        await meds.RecordAsync(med, request, ct);
        return NoContent();
    }

    /// <summary>
    /// Avancement des prises sur la période (défaut : 7 derniers jours) : totaux, par médicament et par jour.
    /// adherence_percent = prises effectuées / prises échues ; les prises à venir ne comptent pas.
    /// </summary>
    [HttpGet("adherence")]
    [ProducesResponseType<AdherenceReportDto>(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<AdherenceReportDto>> Adherence(
        string patientId, [FromQuery] string? from, [FromQuery] string? to, [FromQuery(Name = "as_of")] string? asOf = null, CancellationToken ct = default)
    {
        if (!await access.CanAccessAsync(User, patientId, ct))
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

    private async Task<Medication?> FindAsync(string patientId, string medicationId, CancellationToken ct)
    {
        if (!Ids.IsValid(medicationId) || !await access.CanAccessAsync(User, patientId, ct))
            return null;
        return await db.Medications.Find(m => m.Id == medicationId && m.PatientId == patientId).FirstOrDefaultAsync(ct);
    }
}
