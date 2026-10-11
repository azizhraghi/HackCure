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
    Hypoxia,
    // Ajouts pour le Systeme Multi-Agent (alertes IA qui ne viennent pas d'un seuil capteur)
    Fever,
    Symptom,
    Wound,
    Other
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
