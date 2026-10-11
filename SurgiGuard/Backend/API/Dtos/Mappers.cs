using API.Entites;

namespace API.Dtos;

public static class Mappers
{
    public static UserDto ToDto(this User u) =>
        new(u.Id, u.Email, u.Role, u.FirstName, u.LastName, u.Phone, u.WhatsappNumber);

    public static ThresholdsDto ToDto(this VitalThresholds t) =>
        new() { MinBpm = t.MinBpm, MaxBpm = t.MaxBpm, MinSpo2 = t.MinSpo2 };

    public static MedicalFolderDto ToDto(this MedicalFolder f, string patientId) =>
        new(f.BloodType,
            f.Allergies,
            f.MedicalHistory,
            f.Medications,
            f.Notes,
            f.Documents
                .Select(d => new MedicalDocumentDto(d.Id, d.FileName, d.SizeBytes, $"/api/patients/{patientId}/documents/{d.Id}", d.UploadedAt))
                .ToList(),
            f.UpdatedAt);
}
