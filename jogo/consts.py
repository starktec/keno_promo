from django.db.models import TextChoices, IntegerChoices
from string import digits,ascii_letters,whitespace


class StatusSolicitacaoRecolhe(TextChoices):
    AGUADANDO  = 'A', 'Aguardando'
    CONFIRMADO = 'C', 'Confirmado'
    NEGADO     = 'N', 'Negado'

    @classmethod
    def list_choices(cls) -> list:
        return [t[0] for t in cls.choices]

    @classmethod
    def dict_choices(cls) -> dict:
        return dict(cls.choices) 


class TipoSolicitacaoRecolhe(TextChoices):
    APORTE = 'A','Aporte'
    RECOLHE = 'T','Recolhe'
    
    @classmethod
    def list_choices(cls) -> list:
        return [t[0] for t in cls.choices]

    @classmethod
    def dict_choices(cls) -> dict:
        return dict(cls.choices)

class StatusJogador(IntegerChoices):
    ATIVO = 1, "Ativo"
    SUSPENSO = 2, "Suspenso"
    CANCELADO = 3, "Cancelado"

# nome fantasia = numero + letra -> tudo maiusculo 


class NamesValidations():
    allowed_characters = digits + ascii_letters + whitespace
    allowed_characters_w = digits + ascii_letters

    @staticmethod
    def verify_nome_exist(nome:str,usuario = None):
        from jogo.models import Usuario
        if usuario:
            if Usuario.objects.filter(usuario__first_name__iexact = nome).exclude(id=usuario.id).exists():
                return  True
            else:
                return False
        if Usuario.objects.filter(usuario__first_name__iexact = nome).exists():
            return True
        return False

    @staticmethod
    def verify_login_exist(nome:str,usuario = None ):
        from jogo.models import Usuario
        if usuario:
            if Usuario.objects.filter(usuario__first_name__iexact = nome).exclude(id=usuario.id).exists():
               return  True
            else:
                return False
        if Usuario.objects.filter(usuario__username = nome):
            return True
        return False

    @staticmethod
    def remove_extra_spaces(string:str):
        return " ".join(string.split())

    @classmethod
    def validate_nome(cls,nome:str):
        if set(nome).difference(cls.allowed_characters):
            return False
        return cls.remove_extra_spaces(nome)
    
    @classmethod
    def validate_login(cls,login:str):
        if not login.islower():
            return False
        if set(login).difference(cls.allowed_characters_w):
            return False
        return login

    @classmethod
    def validate_nome_fantasia(cls,nome:str):
        if set(nome).difference(cls.allowed_characters):
            return False
        return " ".join(nome.split()).upper()
         



