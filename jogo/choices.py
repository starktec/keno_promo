from django.db.models import TextChoices,IntegerChoices

class AcaoTipoChoices(TextChoices):
    SEGUIR = "SEGUIR", "Seguir"
    CURTIR = "CURTIR", "Curtir"
    COMENTAR = "COMENTAR", "Comentar"
    RECOMENDAR = "RECOMENDAR", "Marcar"

class StatusCartelaChoice(IntegerChoices):
    RESGATADA  = 1,"Resgatada"
    NAORESGATADA = 2,"Não-resgatada"


UF_CHOICES = (
    ('AC', 'Acre'),
    ('AL', 'Alagoas'),
    ('AP', 'Amapá'),
    ('BA', 'Bahia'),
    ('CE', 'Ceará'),
    ('DF', 'Distrito Federal'),
    ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'),
    ('MA', 'Maranão'),
    ('MG', 'Minas Gerais'),
    ('MS', 'Mato Grosso do Sul'),
    ('MT', 'Mato Grosso'),
    ('PA', 'Pará'),
    ('PB', 'Paraíba'),
    ('PE', 'Pernambuco'),
    ('PI', 'Piauí'),
    ('PR', 'Paraná'),
    ('RJ', 'Rio de Janeiro'),
    ('RN', 'Rio Grande do Norte'),
    ('RO', 'Rondônia'),
    ('RR', 'Roraima'),
    ('RS', 'Rio Grande do Sul'),
    ('SC', 'Santa Catarina'),
    ('SE', 'Sergipe'),
    ('SP', 'São Paulo'),
    ('TO', 'Tocantins')
)
