using API.Entites;
using API.Settings;
using Microsoft.Extensions.Options;
using MongoDB.Driver;
using MongoDB.Driver.GridFS;

namespace API.Data;

public sealed class MongoDbContext
{
    private const string TelemetryCollection = "telemetry";

    private readonly MongoDbSettings _settings;

    public MongoDbContext(IOptions<MongoDbSettings> options)
    {
        _settings = options.Value;
        var client = new MongoClient(_settings.ConnectionString);
        Database = client.GetDatabase(_settings.DatabaseName);
        Documents = new GridFSBucket(Database, new GridFSBucketOptions { BucketName = "medicalDocuments" });
    }

    public IMongoDatabase Database { get; }

    /// <summary>Stockage des PDF du dossier médical.</summary>
    public IGridFSBucket Documents { get; }

    public IMongoCollection<User> Users => Database.GetCollection<User>("users");
    public IMongoCollection<Patient> Patients => Database.GetCollection<Patient>("patients");
    public IMongoCollection<FamilyMember> FamilyMembers => Database.GetCollection<FamilyMember>("familyMembers");
    public IMongoCollection<PatientFamilyRelation> PatientFamilyRelations => Database.GetCollection<PatientFamilyRelation>("patientFamilyRelations");
    public IMongoCollection<TelemetryReading> Telemetry => Database.GetCollection<TelemetryReading>(TelemetryCollection);
    public IMongoCollection<Medication> Medications => Database.GetCollection<Medication>("medications");
    public IMongoCollection<MedicationIntake> MedicationIntakes => Database.GetCollection<MedicationIntake>("medicationIntakes");
    public IMongoCollection<AlertLog> Alerts => Database.GetCollection<AlertLog>("alerts");

    /// <summary>Crée la collection time-series et les index. Idempotent, appelé au démarrage.</summary>
    public async Task EnsureSchemaAsync(CancellationToken ct = default)
    {
        var existing = await (await Database.ListCollectionNamesAsync(cancellationToken: ct)).ToListAsync(ct);
        if (!existing.Contains(TelemetryCollection))
        {
            await Database.CreateCollectionAsync(TelemetryCollection, new CreateCollectionOptions
            {
                TimeSeriesOptions = new TimeSeriesOptions("timestamp", "patientId", TimeSeriesGranularity.Seconds),
                ExpireAfter = TimeSpan.FromDays(_settings.TelemetryRetentionDays)
            }, ct);
        }

        await Users.Indexes.CreateOneAsync(new CreateIndexModel<User>(
            Builders<User>.IndexKeys.Ascending(u => u.Email),
            new CreateIndexOptions { Unique = true }), cancellationToken: ct);

        await Patients.Indexes.CreateManyAsync(
        [
            new CreateIndexModel<Patient>(Builders<Patient>.IndexKeys.Ascending(p => p.UserId), new CreateIndexOptions { Unique = true }),
            new CreateIndexModel<Patient>(Builders<Patient>.IndexKeys.Ascending(p => p.LinkCode), new CreateIndexOptions { Unique = true }),
            new CreateIndexModel<Patient>(Builders<Patient>.IndexKeys.Ascending(p => p.DeviceId), new CreateIndexOptions { Unique = true, Sparse = true })
        ], ct);

        await FamilyMembers.Indexes.CreateOneAsync(new CreateIndexModel<FamilyMember>(
            Builders<FamilyMember>.IndexKeys.Ascending(f => f.UserId),
            new CreateIndexOptions { Unique = true }), cancellationToken: ct);

        await PatientFamilyRelations.Indexes.CreateManyAsync(
        [
            new CreateIndexModel<PatientFamilyRelation>(
                Builders<PatientFamilyRelation>.IndexKeys.Ascending(r => r.PatientId).Ascending(r => r.FamilyMemberId),
                new CreateIndexOptions { Unique = true }),
            new CreateIndexModel<PatientFamilyRelation>(Builders<PatientFamilyRelation>.IndexKeys.Ascending(r => r.FamilyUserId))
        ], ct);

        await Telemetry.Indexes.CreateOneAsync(new CreateIndexModel<TelemetryReading>(
            Builders<TelemetryReading>.IndexKeys.Ascending(t => t.PatientId).Descending(t => t.Timestamp)), cancellationToken: ct);

        await Alerts.Indexes.CreateOneAsync(new CreateIndexModel<AlertLog>(
            Builders<AlertLog>.IndexKeys.Ascending(a => a.PatientId).Descending(a => a.CreatedAt)), cancellationToken: ct);

        await Medications.Indexes.CreateOneAsync(new CreateIndexModel<Medication>(
            Builders<Medication>.IndexKeys.Ascending(m => m.PatientId).Ascending(m => m.CreatedAt)), cancellationToken: ct);

        await MedicationIntakes.Indexes.CreateManyAsync(
        [
            new CreateIndexModel<MedicationIntake>(
                Builders<MedicationIntake>.IndexKeys.Ascending(i => i.MedicationId).Ascending(i => i.Date).Ascending(i => i.Time),
                new CreateIndexOptions { Unique = true }),
            new CreateIndexModel<MedicationIntake>(Builders<MedicationIntake>.IndexKeys.Ascending(i => i.PatientId).Ascending(i => i.Date))
        ], ct);
    }
}
