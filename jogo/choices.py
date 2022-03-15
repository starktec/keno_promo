from django.db.models import TextChoices

class AcaoTipoChoices(TextChoices):
    SEGUIR = "SEGUIR", "Seguir"
    CURTIR = "CURTIR", "Curtir"
    COMENTAR = "COMENTAR", "Comentar"
    RECOMENDAR = "RECOMENDAR", "Recomendar"