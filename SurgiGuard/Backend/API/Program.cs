using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using API.Controllers;
using API.Data;
using API.Security;
using API.Services;
using API.Settings;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using MongoDB.Bson;
using MongoDB.Driver;

MongoConventions.Register();

var builder = WebApplication.CreateBuilder(args);

builder.Services.Configure<MongoDbSettings>(builder.Configuration.GetSection(MongoDbSettings.SectionName));
builder.Services.Configure<JwtSettings>(builder.Configuration.GetSection(JwtSettings.SectionName));
builder.Services.Configure<AuthSettings>(builder.Configuration.GetSection(AuthSettings.SectionName));
builder.Services.Configure<ServiceApiKeysSettings>(builder.Configuration.GetSection(ServiceApiKeysSettings.SectionName));
builder.Services.Configure<WhatsAppSettings>(builder.Configuration.GetSection(WhatsAppSettings.SectionName));
builder.Services.Configure<FirebaseSettings>(builder.Configuration.GetSection(FirebaseSettings.SectionName));

var jwt = builder.Configuration.GetSection(JwtSettings.SectionName).Get<JwtSettings>() ?? new JwtSettings();
if (Encoding.UTF8.GetByteCount(jwt.Key) < 32)
    throw new InvalidOperationException("Jwt:Key doit contenir au moins 32 caractères.");

builder.Services.AddSingleton<MongoDbContext>();
builder.Services.AddSingleton<TokenService>();
builder.Services.AddSingleton<IPushSender, FcmPushSender>();
builder.Services.AddHttpClient<IWhatsAppSender, WhatsAppCloudSender>(c => c.Timeout = TimeSpan.FromSeconds(10));
builder.Services.AddHttpClient(ChatController.HttpClientName, c =>
{
    c.BaseAddress = new Uri(builder.Configuration["ChatService:BaseUrl"]!.TrimEnd('/') + "/");
    c.Timeout = TimeSpan.FromSeconds(30);
});
builder.Services.Configure<MqttSettings>(builder.Configuration.GetSection(MqttSettings.SectionName));
builder.Services.AddHostedService<MqttBridgeService>();
builder.Services.AddScoped<PatientAccessService>();
builder.Services.AddScoped<TelemetryService>();
builder.Services.AddScoped<MedicationService>();
builder.Services.AddScoped<AlertService>();
builder.Services.AddScoped<MedicalFolderService>();

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.MapInboundClaims = false;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidIssuer = jwt.Issuer,
            ValidAudience = jwt.Audience,
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwt.Key)),
            ClockSkew = TimeSpan.FromMinutes(1),
            NameClaimType = Roles.UserIdClaimType,
            RoleClaimType = Roles.ClaimType
        };
    });
builder.Services.AddAuthorization();

builder.Services
    .AddControllers()
    .AddJsonOptions(o =>
    {
        // snake_case : mêmes noms de champs pour l'ESP32, les agents Python et l'app mobile
        o.JsonSerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
        o.JsonSerializerOptions.DictionaryKeyPolicy = JsonNamingPolicy.SnakeCaseLower;
        o.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseUpper));
    });
builder.Services.AddProblemDetails();

builder.Services.AddCors(o => o.AddDefaultPolicy(p => p.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo { Title = "Health Monitoring API", Version = "v1" });
    c.IncludeXmlComments(Path.Combine(AppContext.BaseDirectory, $"{Assembly.GetExecutingAssembly().GetName().Name}.xml"));

    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.Http,
        Scheme = "bearer",
        BearerFormat = "JWT",
        Description = "JWT obtenu via /api/auth/login (app mobile)."
    });
    c.AddSecurityDefinition("ApiKey", new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.ApiKey,
        In = ParameterLocation.Header,
        Name = ServiceApiKeyAttribute.HeaderName,
        Description = "Clé des clients machine (passerelle IoT, Système Multi-Agent)."
    });
    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        [new OpenApiSecurityScheme { Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "Bearer" } }] = [],
        [new OpenApiSecurityScheme { Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "ApiKey" } }] = []
    });
});

var app = builder.Build();

await app.Services.GetRequiredService<MongoDbContext>().EnsureSchemaAsync();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment() || app.Configuration.GetValue<bool>("EnableSwagger"))
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

app.MapGet("/health", async (MongoDbContext db, CancellationToken ct) =>
{
    await db.Database.RunCommandAsync<BsonDocument>(new BsonDocument("ping", 1), cancellationToken: ct);
    return Results.Ok(new { status = "ok" });
}).ExcludeFromDescription();

app.Run();
