namespace API.Entites;

public enum UserRole
{
    Patient,
    FamilyMember,
    Nurse,
    Doctor
}

public enum AlertType
{
    Fall,
    Tachycardia,
    Bradycardia,
    Hypoxia
}

public enum AlertStatus
{
    Open,
    Acknowledged,
    Resolved
}

public enum NotificationChannel
{
    Whatsapp,
    Push
}
