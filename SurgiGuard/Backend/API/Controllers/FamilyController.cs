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
[Authorize(Roles = Roles.FamilyMember)]
[Route("api/family")]
[Produces("application/json")]
public sealed class FamilyController(MongoDbContext db, TelemetryService telemetry) : ControllerBase
{
    /// <summary>Lie le proche connecté à un patient via le code affiché dans l'app du patient.</summary>
    [HttpPost("link-patient")]
    [ProducesResponseType<FollowedPatientDto>(StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<ActionResult<FollowedPatientDto>> LinkPatient(LinkPatientRequest request, CancellationToken ct)
    {
        var userId = User.GetUserId();
        var user = await db.Users.Find(u => u.Id == userId).FirstAsync(ct);
        var member = await db.FamilyMembers.Find(f => f.UserId == userId).FirstOrDefaultAsync(ct);
        if (member is null)
            return Problem(statusCode: StatusCodes.Status404NotFound, title: "Profil proche introuvable.");

        if (request.WhatsappOptIn && string.IsNullOrEmpty(user.WhatsappNumber))
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "Ajoutez un numéro WhatsApp avant d'activer les alertes WhatsApp.");

        var code = request.LinkCode.Trim();
        var patient = await db.Patients.Find(p => p.LinkCode == code).FirstOrDefaultAsync(ct);
        if (patient is null)
            return Problem(statusCode: StatusCodes.Status404NotFound, title: "Code de liaison invalide.");

        // Sans contact principal, les alertes de gravité 2 ne partiraient sur WhatsApp vers personne
        var isPrimary = request.IsPrimaryContact
                        || !await db.PatientFamilyRelations.Find(r => r.PatientId == patient.Id && r.IsPrimaryContact).AnyAsync(ct);

        var relation = new PatientFamilyRelation
        {
            PatientId = patient.Id,
            FamilyMemberId = member.Id,
            FamilyUserId = userId,
            Relationship = request.Relationship.Trim(),
            WhatsappOptIn = request.WhatsappOptIn,
            IsPrimaryContact = isPrimary
        };

        try
        {
            await db.PatientFamilyRelations.InsertOneAsync(relation, cancellationToken: ct);
        }
        catch (MongoWriteException ex) when (ex.WriteError.Category == ServerErrorCategory.DuplicateKey)
        {
            return Problem(statusCode: StatusCodes.Status409Conflict, title: "Vous suivez déjà ce patient.");
        }

        // Un seul contact principal par patient
        if (relation.IsPrimaryContact)
        {
            await db.PatientFamilyRelations.UpdateManyAsync(
                r => r.PatientId == patient.Id && r.Id != relation.Id,
                Builders<PatientFamilyRelation>.Update.Set(r => r.IsPrimaryContact, false),
                cancellationToken: ct);
        }

        var dto = await ToDtoAsync(patient, relation, ct);
        return StatusCode(StatusCodes.Status201Created, dto);
    }

    /// <summary>Patients suivis par le proche connecté, avec leur dernière mesure.</summary>
    [HttpGet("patients")]
    [ProducesResponseType<IReadOnlyList<FollowedPatientDto>>(StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<FollowedPatientDto>>> GetPatients(CancellationToken ct)
    {
        var userId = User.GetUserId();
        var relations = await db.PatientFamilyRelations.Find(r => r.FamilyUserId == userId).ToListAsync(ct);
        var patientIds = relations.Select(r => r.PatientId).ToList();
        var patients = (await db.Patients.Find(Builders<Patient>.Filter.In(p => p.Id, patientIds)).ToListAsync(ct))
            .ToDictionary(p => p.Id);

        var result = new List<FollowedPatientDto>();
        foreach (var relation in relations.Where(r => patients.ContainsKey(r.PatientId)))
            result.Add(await ToDtoAsync(patients[relation.PatientId], relation, ct));

        return Ok(result);
    }

    private async Task<FollowedPatientDto> ToDtoAsync(Patient patient, PatientFamilyRelation relation, CancellationToken ct)
    {
        var patientUser = await db.Users.Find(u => u.Id == patient.UserId).FirstOrDefaultAsync(ct);
        var latest = await telemetry.GetLatestAsync(patient.Id, ct);

        return new FollowedPatientDto(
            patient.Id,
            patientUser?.FullName ?? "",
            patient.DateOfBirth,
            patient.DeviceId,
            relation.Relationship,
            relation.IsPrimaryContact,
            relation.WhatsappOptIn,
            relation.LinkedAt,
            latest is null ? null : TelemetryDto.From(latest));
    }
}
