using System.Globalization;
using API.Data;
using API.Dtos;
using API.Entites;
using MongoDB.Driver;

namespace API.Services;

/// <summary>Planification des prises, enregistrement des réponses du patient et calcul de l'avancement.</summary>
public sealed class MedicationService(MongoDbContext db)
{
    public const int MaxRangeDays = 62;
    private const string DateFormat = "yyyy-MM-dd";
    private const string TimeFormat = "HH:mm";

    public static bool TryParseDate(string? s, out DateOnly d) =>
        DateOnly.TryParseExact(s, DateFormat, CultureInfo.InvariantCulture, DateTimeStyles.None, out d);

    /// <summary>Valide « HH:mm », supprime les doublons et trie.</summary>
    public static bool TryNormalizeTimes(IEnumerable<string>? times, out List<string> normalized)
    {
        normalized = [];
        if (times is null)
            return false;
        var set = new SortedSet<string>(StringComparer.Ordinal);
        foreach (var t in times)
        {
            if (!TimeOnly.TryParseExact(t?.Trim(), TimeFormat, CultureInfo.InvariantCulture, DateTimeStyles.None, out var parsed))
                return false;
            set.Add(parsed.ToString(TimeFormat, CultureInfo.InvariantCulture));
        }
        normalized = [.. set];
        return normalized.Count > 0;
    }

    public static string Fmt(DateOnly d) => d.ToString(DateFormat, CultureInfo.InvariantCulture);

    /// <summary>Heure locale du patient au moment de la requête : fournie par le client (as_of), sinon l'heure serveur UTC.</summary>
    public static bool TryParseAsOf(string? s, out DateTime asOf)
    {
        if (string.IsNullOrWhiteSpace(s))
        {
            asOf = DateTime.UtcNow;
            return true;
        }
        return DateTime.TryParseExact(s, ["yyyy-MM-ddTHH:mm", "yyyy-MM-ddTHH:mm:ss"], CultureInfo.InvariantCulture, DateTimeStyles.None, out asOf);
    }

    public Task<List<Medication>> ListAsync(string patientId, bool includeStopped, CancellationToken ct) =>
        db.Medications.Find(includeStopped ? m => m.PatientId == patientId : m => m.PatientId == patientId && m.Active)
            .SortBy(m => m.CreatedAt)
            .ToListAsync(ct);

    public async Task<List<DoseDto>> ScheduleAsync(string patientId, DateOnly from, int days, DateTime asOf, CancellationToken ct)
    {
        var to = from.AddDays(days - 1);
        var meds = await db.Medications.Find(m => m.PatientId == patientId).ToListAsync(ct);
        var intakes = await LoadIntakesAsync(patientId, from, to, ct);
        return Expand(meds, intakes, from, to, asOf);
    }

    public async Task<AdherenceReportDto> AdherenceAsync(string patientId, DateOnly from, DateOnly to, DateTime asOf, CancellationToken ct)
    {
        var meds = await db.Medications.Find(m => m.PatientId == patientId).ToListAsync(ct);
        var intakes = await LoadIntakesAsync(patientId, from, to, ct);
        var doses = Expand(meds, intakes, from, to, asOf);

        return new AdherenceReportDto(
            patientId, Fmt(from), Fmt(to), asOf.ToString("yyyy-MM-ddTHH:mm", CultureInfo.InvariantCulture),
            Count(doses),
            doses.GroupBy(d => d.MedicationId).Select(g => new MedicationAdherenceDto(g.Key, g.First().Name, Count(g))).OrderBy(m => m.Name).ToList(),
            doses.GroupBy(d => d.Date).OrderBy(g => g.Key).Select(g => new DayAdherenceDto(g.Key, Count(g))).ToList());
    }

    /// <summary>Enregistre (upsert) ou annule (status null) la réponse du patient pour une prise planifiée.</summary>
    public async Task<bool> RecordAsync(Medication med, RecordIntakeRequest request, CancellationToken ct)
    {
        var filter = Builders<MedicationIntake>.Filter.Where(i => i.MedicationId == med.Id && i.Date == request.Date && i.Time == request.Time);
        if (request.Status is null)
        {
            await db.MedicationIntakes.DeleteOneAsync(filter, ct);
            return true;
        }

        await db.MedicationIntakes.UpdateOneAsync(
            filter,
            Builders<MedicationIntake>.Update
                .Set(i => i.Status, request.Status.Value)
                .Set(i => i.RecordedAt, DateTime.UtcNow)
                .SetOnInsert(i => i.PatientId, med.PatientId),
            new UpdateOptions { IsUpsert = true },
            ct);
        return true;
    }

    private Task<List<MedicationIntake>> LoadIntakesAsync(string patientId, DateOnly from, DateOnly to, CancellationToken ct)
    {
        var f = Fmt(from);
        var t = Fmt(to);
        // Les dates ISO se comparent correctement comme des chaînes
        return db.MedicationIntakes.Find(i => i.PatientId == patientId && i.Date.CompareTo(f) >= 0 && i.Date.CompareTo(t) <= 0).ToListAsync(ct);
    }

    private static List<DoseDto> Expand(List<Medication> meds, List<MedicationIntake> intakes, DateOnly from, DateOnly to, DateTime asOf)
    {
        var byKey = intakes.ToDictionary(i => (i.MedicationId, i.Date, i.Time));
        var doses = new List<DoseDto>();
        foreach (var m in meds)
        {
            if (!TryParseDate(m.StartDate, out var start))
                continue;
            var end = TryParseDate(m.EndDate, out var e) ? e : DateOnly.MaxValue;
            var first = start > from ? start : from;
            var last = end < to ? end : to;
            for (var day = first; day <= last; day = day.AddDays(1))
            {
                var date = Fmt(day);
                foreach (var time in m.Times)
                {
                    DoseStatus status;
                    DateTime? recordedAt = null;
                    if (byKey.TryGetValue((m.Id, date, time), out var intake))
                    {
                        status = intake.Status == IntakeStatus.Taken ? DoseStatus.Taken : DoseStatus.Skipped;
                        recordedAt = intake.RecordedAt;
                    }
                    else
                    {
                        var at = day.ToDateTime(TimeOnly.ParseExact(time, TimeFormat, CultureInfo.InvariantCulture));
                        status = at < asOf ? DoseStatus.Missed : DoseStatus.Pending;
                    }
                    doses.Add(new DoseDto(m.Id, m.Name, m.Dosage, m.Instructions, date, time, status, recordedAt));
                }
            }
        }
        return doses.OrderBy(d => d.Date, StringComparer.Ordinal).ThenBy(d => d.Time, StringComparer.Ordinal).ThenBy(d => d.Name).ToList();
    }

    /// <summary>Adhérence = prises effectuées / prises échues (effectuées + ignorées + manquées) ; les prises à venir n'comptent pas.</summary>
    private static AdherenceCounts Count(IEnumerable<DoseDto> doses)
    {
        int taken = 0, skipped = 0, missed = 0, pending = 0;
        foreach (var d in doses)
        {
            switch (d.Status)
            {
                case DoseStatus.Taken: taken++; break;
                case DoseStatus.Skipped: skipped++; break;
                case DoseStatus.Missed: missed++; break;
                default: pending++; break;
            }
        }
        var due = taken + skipped + missed;
        return new AdherenceCounts(due + pending, taken, skipped, missed, pending, due == 0 ? null : Math.Round(100.0 * taken / due, 1));
    }
}
