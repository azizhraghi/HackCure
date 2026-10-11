using System.Security.Claims;
using API.Data;
using API.Entites;
using API.Security;
using MongoDB.Driver;

namespace API.Services;

/// <summary>
/// Qui peut lire les données d'un patient : le patient lui-même, les proches liés,
/// et le personnel soignant (NURSE / DOCTOR, sans affectation pour le hackathon).
/// </summary>
public sealed class PatientAccessService(MongoDbContext db)
{
    public async Task<bool> CanAccessAsync(ClaimsPrincipal principal, string patientId, CancellationToken ct)
    {
        if (!Ids.IsValid(patientId))
            return false;

        var userId = principal.GetUserId();
        return principal.GetRole() switch
        {
            UserRole.Doctor or UserRole.Nurse => true,
            UserRole.Patient => await db.Patients.Find(p => p.Id == patientId && p.UserId == userId).AnyAsync(ct),
            UserRole.FamilyMember => await db.PatientFamilyRelations.Find(r => r.PatientId == patientId && r.FamilyUserId == userId).AnyAsync(ct),
            _ => false
        };
    }
}
