using API.Data;
using API.Dtos;
using API.Entites;
using MongoDB.Bson;
using MongoDB.Driver;

namespace API.Services;

public sealed record IngestResult(Patient Patient, TelemetryReading Reading, IReadOnlyList<AlertType> Anomalies);

public sealed class TelemetryService(MongoDbContext db)
{
    public const int MaxPoints = 2000;

    /// <summary>
    /// Enregistre une mesure. Le boîtier (device_id) fait foi pour identifier le patient ;
    /// renvoie null si aucun patient ne correspond.
    /// </summary>
    public async Task<IngestResult?> IngestAsync(TelemetryIngestRequest request, CancellationToken ct)
    {
        var patient = await ResolvePatientAsync(request, ct);
        if (patient is null)
            return null;

        var reading = new TelemetryReading
        {
            PatientId = patient.Id,
            DeviceId = request.DeviceId?.Trim() ?? patient.DeviceId,
            Timestamp = NormalizeTimestamp(request.Timestamp),
            Bpm = request.Bpm,
            Spo2 = request.Spo2,
            RoomTemp = request.RoomTemp,
            RoomHumidity = request.RoomHumidity,
            MotionState = request.MotionState?.Trim().ToUpperInvariant(),
            FallDetected = request.FallDetected
        };
        await db.Telemetry.InsertOneAsync(reading, cancellationToken: ct);

        return new IngestResult(patient, reading, DetectAnomalies(reading, patient.Thresholds));
    }

    public static IReadOnlyList<AlertType> DetectAnomalies(TelemetryReading r, VitalThresholds t)
    {
        var anomalies = new List<AlertType>();
        if (r.FallDetected)
            anomalies.Add(AlertType.Fall);
        if (r.Bpm > t.MaxBpm)
            anomalies.Add(AlertType.Tachycardia);
        // 0 = capteur non porté, pas une bradycardie
        if (r.Bpm > 0 && r.Bpm < t.MinBpm)
            anomalies.Add(AlertType.Bradycardia);
        if (r.Spo2 > 0 && r.Spo2 < t.MinSpo2)
            anomalies.Add(AlertType.Hypoxia);
        return anomalies;
    }

    public Task<TelemetryReading?> GetLatestAsync(string patientId, CancellationToken ct) =>
        db.Telemetry.Find(t => t.PatientId == patientId)
            .SortByDescending(t => t.Timestamp)
            .FirstOrDefaultAsync(ct)!;

    /// <summary>intervalMinutes = 0 : mesures brutes (les plus récentes) ; sinon moyennes par tranche.</summary>
    public async Task<IReadOnlyList<TelemetryPointDto>> GetHistoryAsync(
        string patientId, DateTime from, DateTime to, int intervalMinutes, CancellationToken ct)
    {
        if (intervalMinutes == 0)
        {
            var readings = await db.Telemetry
                .Find(t => t.PatientId == patientId && t.Timestamp >= from && t.Timestamp <= to)
                .SortByDescending(t => t.Timestamp)
                .Limit(MaxPoints)
                .ToListAsync(ct);

            return readings
                .AsEnumerable()
                .Reverse()
                .Select(r => new TelemetryPointDto(r.Timestamp, r.Bpm, r.Spo2, r.RoomTemp, r.RoomHumidity, r.FallDetected, 1))
                .ToList();
        }

        PipelineDefinition<TelemetryReading, BsonDocument> pipeline = new[]
        {
            new BsonDocument("$match", new BsonDocument
            {
                { "patientId", ObjectId.Parse(patientId) },
                { "timestamp", new BsonDocument { { "$gte", from }, { "$lte", to } } }
            }),
            new BsonDocument("$group", new BsonDocument
            {
                {
                    "_id", new BsonDocument("$dateTrunc", new BsonDocument
                    {
                        { "date", "$timestamp" }, { "unit", "minute" }, { "binSize", intervalMinutes }
                    })
                },
                { "bpm", new BsonDocument("$avg", "$bpm") },
                { "spo2", new BsonDocument("$avg", "$spo2") },
                { "roomTemp", new BsonDocument("$avg", "$roomTemp") },
                { "roomHumidity", new BsonDocument("$avg", "$roomHumidity") },
                { "falls", new BsonDocument("$sum", new BsonDocument("$cond", new BsonArray { "$fallDetected", 1, 0 })) },
                { "samples", new BsonDocument("$sum", 1) }
            }),
            new BsonDocument("$sort", new BsonDocument("_id", 1)),
            new BsonDocument("$limit", MaxPoints)
        };

        var buckets = await db.Telemetry.Aggregate(pipeline, cancellationToken: ct).ToListAsync(ct);
        return buckets
            .Select(b => new TelemetryPointDto(
                b["_id"].ToUniversalTime(),
                Avg(b, "bpm"),
                Avg(b, "spo2"),
                Avg(b, "roomTemp"),
                Avg(b, "roomHumidity"),
                b["falls"].ToInt32() > 0,
                b["samples"].ToInt32()))
            .ToList();
    }

    private async Task<Patient?> ResolvePatientAsync(TelemetryIngestRequest request, CancellationToken ct)
    {
        if (!string.IsNullOrWhiteSpace(request.DeviceId))
        {
            var deviceId = request.DeviceId.Trim();
            return await db.Patients.Find(p => p.DeviceId == deviceId).FirstOrDefaultAsync(ct);
        }

        return Ids.IsValid(request.PatientId)
            ? await db.Patients.Find(p => p.Id == request.PatientId).FirstOrDefaultAsync(ct)
            : null;
    }

    /// <summary>Sans NTP l'ESP32 envoie souvent 1970 : on retombe sur l'heure serveur si la valeur n'est pas plausible.</summary>
    private static DateTime NormalizeTimestamp(DateTime? timestamp)
    {
        var now = DateTime.UtcNow;
        if (timestamp is null)
            return now;

        var utc = timestamp.Value.Kind == DateTimeKind.Unspecified
            ? DateTime.SpecifyKind(timestamp.Value, DateTimeKind.Utc)
            : timestamp.Value.ToUniversalTime();
        return utc > now.AddMinutes(5) || utc < now.AddDays(-7) ? now : utc;
    }

    private static double? Avg(BsonDocument doc, string field) =>
        doc.TryGetValue(field, out var v) && !v.IsBsonNull ? Math.Round(v.ToDouble(), 1) : null;
}
