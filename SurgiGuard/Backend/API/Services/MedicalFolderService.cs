using API.Data;
using API.Dtos;
using API.Entites;
using MongoDB.Bson;
using MongoDB.Driver;
using MongoDB.Driver.GridFS;

namespace API.Services;

public sealed class MedicalFolderService(MongoDbContext db)
{
    public const long MaxPdfBytes = 10 * 1024 * 1024;
    public const int MaxDocuments = 20;
    private const int MaxListItems = 100;
    private const int MaxItemLength = 300;

    /// <summary>Renvoie un message d'erreur, ou null si le formulaire est valide.</summary>
    public static string? Validate(MedicalFolderUpdateForm form, MedicalFolder current)
    {
        foreach (var (name, list) in new[] { ("allergies", form.Allergies), ("medical_history", form.MedicalHistory), ("medications", form.Medications) })
        {
            if (list.Count > MaxListItems)
                return $"'{name}' : {MaxListItems} éléments maximum.";
            if (list.Any(item => item?.Length > MaxItemLength))
                return $"'{name}' : {MaxItemLength} caractères maximum par élément.";
        }

        var remaining = current.Documents.Count(d => !form.RemoveDocumentIds.Contains(d.Id));
        if (remaining + form.Documents.Count > MaxDocuments)
            return $"{MaxDocuments} documents maximum par dossier.";

        foreach (var file in form.Documents)
        {
            if (file.Length is 0 or > MaxPdfBytes)
                return $"'{file.FileName}' : taille invalide (10 Mo maximum).";
            if (!IsPdf(file))
                return $"'{file.FileName}' n'est pas un PDF.";
        }

        return null;
    }

    public async Task<MedicalFolder> UpdateAsync(Patient patient, MedicalFolderUpdateForm form, CancellationToken ct)
    {
        var folder = patient.MedicalFolder;
        folder.BloodType = string.IsNullOrWhiteSpace(form.BloodType) ? null : form.BloodType.Trim().ToUpperInvariant();
        folder.Allergies = Clean(form.Allergies);
        folder.MedicalHistory = Clean(form.MedicalHistory);
        folder.Medications = Clean(form.Medications);
        folder.Notes = string.IsNullOrWhiteSpace(form.Notes) ? null : form.Notes.Trim();

        foreach (var doc in folder.Documents.Where(d => form.RemoveDocumentIds.Contains(d.Id)).ToList())
        {
            try
            {
                await db.Documents.DeleteAsync(ObjectId.Parse(doc.Id), ct);
            }
            catch (GridFSFileNotFoundException)
            {
                // déjà supprimé : on nettoie seulement la référence
            }
            folder.Documents.Remove(doc);
        }

        foreach (var file in form.Documents)
        {
            var fileName = Path.GetFileName(file.FileName);
            await using var stream = file.OpenReadStream();
            var fileId = await db.Documents.UploadFromStreamAsync(fileName, stream, new GridFSUploadOptions
            {
                Metadata = new BsonDocument
                {
                    { "patientId", ObjectId.Parse(patient.Id) },
                    { "contentType", "application/pdf" }
                }
            }, ct);
            folder.Documents.Add(new MedicalDocument { Id = fileId.ToString(), FileName = fileName, SizeBytes = file.Length });
        }

        folder.UpdatedAt = DateTime.UtcNow;
        await db.Patients.UpdateOneAsync(
            p => p.Id == patient.Id,
            Builders<Patient>.Update.Set(p => p.MedicalFolder, folder),
            cancellationToken: ct);
        return folder;
    }

    /// <summary>Ouvre un PDF du dossier ; null s'il n'appartient pas à ce patient.</summary>
    public async Task<(Stream Content, MedicalDocument Document)?> OpenAsync(Patient patient, string documentId, CancellationToken ct)
    {
        var document = patient.MedicalFolder.Documents.FirstOrDefault(d => d.Id == documentId);
        if (document is null)
            return null;

        try
        {
            var stream = await db.Documents.OpenDownloadStreamAsync(ObjectId.Parse(document.Id), cancellationToken: ct);
            return (stream, document);
        }
        catch (GridFSFileNotFoundException)
        {
            return null;
        }
    }

    private static bool IsPdf(IFormFile file)
    {
        using var stream = file.OpenReadStream();
        Span<byte> header = stackalloc byte[5];
        return stream.ReadAtLeast(header, header.Length, throwOnEndOfStream: false) == header.Length
               && header.SequenceEqual("%PDF-"u8);
    }

    private static List<string> Clean(IEnumerable<string?> items) =>
        items.Where(i => !string.IsNullOrWhiteSpace(i))
            .Select(i => i!.Trim())
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
}
