import datetime

from django import forms
from django.core.exceptions import ValidationError
from jogo.choices import StatusCartelaChoice

from jogo.consts import NamesValidations
from jogo.models import TemplatePartida, Usuario, Partida, PARTIDA_TIPOS_CHOICES, \
    Configuracao, TEMPO_CHOICES, TEMPO_LIBERAR_CHOICES, TEMPO_MINIMO_ANTECIPADO
from jogo.utils import testa_horario


class NovaPartidaAutomatizada(forms.Form):
    dia_partida_inicial = forms.CharField(initial=datetime.datetime.today(),widget=forms.DateInput(
        attrs={'data-date-format': "dd/mm/yyyy", 'data-provide': "datepicker",
               'class': "form-control form-control-lg form-control-outlined date-picker inputIni inputFim",
               'autocomplete': "off", 'onChange':"testa_antecipado()"}))
    hora_partida_inicial = forms.CharField(widget=forms.TimeInput(
        attrs={'type': "time", 'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    valor_kuadra_inicial = forms.DecimalField(initial = 10,widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off", 'type': "number"}))
    valor_kina_inicial = forms.DecimalField(initial = 10,widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off", 'type': "number"}))
    valor_keno_inicial = forms.DecimalField(initial = 40,widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off", 'type': "number"}))
    tempo_partidas = forms.IntegerField(initial=10,widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    limite_partidas = forms.IntegerField(initial = 100,widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"})) 
    tipo_rodada = forms.ChoiceField(
        widget=forms.Select(attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}),
        choices=PARTIDA_TIPOS_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_dia_partida(self):
        valor = self.cleaned_data['dia_partida']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        return valor

    def clean_hora_partida(self):
        valor = self.cleaned_data['hora_partida']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        return valor

    def clean_tipo_rodada(self):
        valor = self.cleaned_data['tipo_rodada']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        return valor


    def clean_valor_kuadra(self):
        valor = self.cleaned_data['valor_kuadra']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        if valor <= 0:
            raise ValidationError(
                "Por favor, informe um valor válido")
        return valor

    def clean_valor_kina(self):
        valor = self.cleaned_data['valor_kina']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        if valor <= 0:
            raise ValidationError(
                "Por favor, informe um valor válido")
        return valor

    def clean_valor_keno(self):
        valor = self.cleaned_data['valor_keno']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        if valor <= 0:
            raise ValidationError(
                "Por favor, informe um valor válido")
        return valor


    def clean(self):
        cleaned_data = super().clean()
        dia = cleaned_data.get("dia_partida_inicial")
        hora = cleaned_data.get("hora_partida_inicial")

        kuadra = cleaned_data.get("valor_kuadra")
        kina = cleaned_data.get("valor_kina")
        keno = cleaned_data.get("valor_keno")

        if dia and hora:
            dataValor = datetime.datetime.strptime(dia + " " + hora, "%d/%m/%Y %H:%M")
            if Partida.objects.filter(data_partida=dataValor).exists():
                raise ValidationError(
                    "Já existe uma partida agendada para essa data"
                )
            partidas = Partida.objects.filter(data_partida__lt=dataValor).order_by(
                '-data_partida')
            if partidas:
                configuracao = Configuracao.objects.last()
                mais_proxima = partidas[0].data_partida
                diferenca = dataValor - mais_proxima
                if diferenca.total_seconds() < (configuracao.tempo_min_entre_sorteios * 60):
                    msg = "Exite uma partida agendada as " + mais_proxima.strftime("%d/%m/%Y %H:%M:%S")
                    msg += " e o próximo horário disponível é as " + (
                            mais_proxima + datetime.timedelta(minutes=10)).strftime("%d/%m/%Y %H:%M:%S")
                    raise ValidationError(msg)

            dataAtual = datetime.datetime.now()
            if dataValor <= dataAtual:
                raise ValidationError(
                    "Você não pode agendar uma partida para uma data anterior a atual"
                )

        if kuadra and kina and keno and (kuadra > kina or kuadra >= keno or kina >= keno):
            raise ValidationError(
                "O valor da kuadra deve ser menor ou igual que a da kina assim como o valor de ambos deve ser menor que o valor do keno"
            )
class NovaPartidaForm(forms.ModelForm):
    dia_partida = forms.CharField(widget=forms.DateInput(
        attrs={'type': 'text', 'data-date-format': "dd/mm/yyyy", 'data-provide': "datepicker",
               'class': "form-control form-control-lg form-control-outlined date-picker inputIni inputFim",
               'autocomplete': "off", 'onChange':"datapickerADS($('#id_dia_partida').val())"}))
    hora_partida = forms.CharField(widget=forms.TimeInput(
        attrs={'type': "time", 'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    tipo_rodada = forms.ChoiceField(
        widget=forms.Select(attrs={'class': "form-select-lg form-control form-control-outlined", 'autocomplete': "off"}),
        choices=PARTIDA_TIPOS_CHOICES, required=False)
    nome_sorteio = forms.CharField(
        widget=forms.TextInput(attrs={'class':"form-control form-control-lg form-control-outlined", 'maxlength': "17",
                                     'autocomplete': "off"}), required=False)
    hora_virada = forms.TimeField(required=False, widget=forms.TimeInput(
        attrs={'type': "time", 'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    valor_kuadra = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off", 'type': "number"}))
    valor_kina = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off", 'type': "number"}))
    valor_keno = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off", 'type': "number"}))
    numero_cartelas_iniciais = forms.IntegerField(
        min_value=1,max_value=30000,
        widget=forms.NumberInput(
            attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off", 'type': "number"}
        ), initial=500
    )
    chance_vitoria = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off", 'type': "number"}),
        initial=100.0
    )


    class Meta:
        model = Partida
        fields = ['valor_kuadra', 'valor_kina', 'valor_keno',
                  'dia_partida', 'hora_partida', 'tipo_rodada',"chance_vitoria",
                  'nome_sorteio','hora_virada','numero_cartelas_iniciais']

    def clean_dia_partida(self):
        valor = self.cleaned_data['dia_partida']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )

        return valor

    def clean_hora_partida(self):
        valor = self.cleaned_data['hora_partida']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        return valor

    def clean_tipo_rodada(self):
        valor = self.cleaned_data['tipo_rodada']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        return valor


    def clean_valor_kuadra(self):
        valor = self.cleaned_data['valor_kuadra']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        if valor <= 0:
            raise ValidationError(
                "Por favor, informe um valor válido")
        return valor

    def clean_valor_kina(self):
        valor = self.cleaned_data['valor_kina']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        if valor <= 0:
            raise ValidationError(
                "Por favor, informe um valor válido")
        return valor

    def clean_valor_keno(self):
        valor = self.cleaned_data['valor_keno']
        if not valor:
            raise ValidationError(
                "Por favor, preencha este campo obrigatorio!"
            )
        if valor <= 0:
            raise ValidationError(
                "Por favor, informe um valor válido")
        return valor

    def clean(self):
        cleaned_data = super().clean()
        dia = cleaned_data.get("dia_partida")
        hora = cleaned_data.get("hora_partida")
        kuadra = cleaned_data.get("valor_kuadra")
        kina = cleaned_data.get("valor_kina")
        keno = cleaned_data.get("valor_keno")

        if dia and hora:
            dataValor = datetime.datetime.strptime(dia + " " + hora, "%d/%m/%Y %H:%M")

            if Partida.objects.filter(data_partida=dataValor,).exists():
                raise ValidationError(
                    "Já existe uma partida agendada para essa data"
                )
            partida_anterior = Partida.objects.filter(data_partida__lt=dataValor, ).order_by(
                '-data_partida').first()
            partida_posterior = Partida.objects.filter(data_partida__gt=dataValor, ).order_by(
                'data_partida').first()
            if partida_anterior or partida_posterior:
                configuracao = Configuracao.objects.last()
                mais_proxima_anterior = partida_anterior.data_partida if partida_anterior else None
                mais_proxima_posterior = partida_posterior.data_partida if partida_posterior else None
                diferenca = None
                diferenca_depois = None
                diferenca_antes = None
                if mais_proxima_anterior:
                    diferenca = dataValor - mais_proxima_anterior
                    diferenca_antes = diferenca
                if mais_proxima_posterior:
                    diferenca_depois = mais_proxima_posterior - dataValor
                    if diferenca_antes:
                        diferenca = min([diferenca_antes,diferenca_depois])
                    else:
                        diferenca = diferenca_depois
                if diferenca.total_seconds() < (configuracao.tempo_min_entre_sorteios * 60):
                    msg = "Existe uma partida agendada próxima as "
                    if diferenca == diferenca_depois:
                        msg += mais_proxima_posterior.strftime("%d/%m/%Y %H:%M:%S")
                        msg += ". O próximo horário disponível é as "
                        msg += testa_horario(mais_proxima_posterior).strftime("%d/%m/%Y %H:%M:%S")
                    elif diferenca == diferenca_antes:
                        msg += mais_proxima_anterior.strftime("%d/%m/%Y %H:%M:%S")
                        msg += ". O próximo horário disponível é as "
                        msg += testa_horario(mais_proxima_anterior).strftime("%d/%m/%Y %H:%M:%S")

                    raise ValidationError(msg)

            dataAtual = datetime.datetime.now()
            if dataValor <= dataAtual:
                raise ValidationError(
                    "Você não pode agendar uma partida para uma data anterior a atual"
                )


        if kuadra and kina and keno and (kuadra > kina or kuadra >= keno or kina >= keno):
            raise ValidationError(
                "O valor da kuadra deve ser menor ou igual que a da kina assim como o valor de ambos deve ser menor que o valor do keno"
            )

class GanhadoresForm(forms.Form):
    data_inicio = forms.CharField(required=False, widget=forms.TextInput(attrs={'data-date-format': "dd/mm/yyyy",
                                                                                'class': "form-control date-picker form-control-lg form-control-outlined input-search-financeiro",
                                                                                'autocomplete': "off"}))
    data_fim = forms.CharField(required=False, widget=forms.TextInput(attrs={'data-date-format': "dd/mm/yyyy",
                                                                             'class': "form-control date-picker form-control-lg form-control-outlined input-search-financeiro",
                                                                             'autocomplete': "off"}))
    partida = forms.IntegerField(required=False,
                                 widget=forms.NumberInput(
                                     attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))

class JogadoresForm(forms.Form):
    data_inicio = forms.CharField(required=False, widget=forms.TextInput(attrs={'data-date-format': "dd/mm/yyyy",
                                                                                'class': "form-control date-picker form-control-lg form-control-outlined input-search-financeiro",
                                                                                'autocomplete': "off"}))
    data_fim = forms.CharField(required=False, widget=forms.TextInput(attrs={'data-date-format': "dd/mm/yyyy",
                                                                             'class': "form-control date-picker form-control-lg form-control-outlined input-search-financeiro",
                                                                             'autocomplete': "off"}))
    nome_jogador = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"
    }))
    partida = forms.IntegerField(required=False,
                                 widget=forms.NumberInput(
                                     attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))


class UsuarioForm(forms.Form):
    id = forms.HiddenInput()
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"
    }))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"
    }))
    username = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"
    }))


class UsuarioAddForm(forms.Form):
    nome = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    sobrenome = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    cpf = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined",'autocomplete': "off",
        "onkeypress": 'return event.charCode >= 48 && event.charCode <= 57'}))
    fone = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    email = forms.EmailField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    senha = forms.CharField(required=False, widget=forms.PasswordInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    senha_novamente = forms.CharField(required=False, widget=forms.PasswordInput(
        attrs={'class': "form-control form-control-lg form-control-outlined"}))
    login = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined"}))

    usuario_id = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_login(self):
        usuario_id = self.data.get('usuario_id')
        if usuario_id:
            usuario = Usuario.objects.get(id = usuario_id)
        else:
            usuario = None
        valor = self.cleaned_data['login']
        if not valor:
            raise ValidationError(
                "Campo obrigatorio!"
            )
        login = NamesValidations.validate_login(valor)
        if not login:
            raise ValidationError(
                "Formato inválido use apenas letras minúsculas e numeros!"
            )
        if NamesValidations.verify_login_exist(login,usuario):
            raise ValidationError(
                "Login já cadastrado!"
            )
        return login

    def clean_senha(self):
        valor = self.cleaned_data['senha']
        if not valor:
            raise ValidationError(
                "Campo obrigatorio!"
            )
        return valor

    def clean_senha_novamente(self):
        valor = self.cleaned_data['senha_novamente']
        if not valor:
            raise ValidationError(
                "Campo obrigatorio!"
            )
        return valor

    def clean_nome(self):
        usuario_id = self.data.get('usuario_id')
        if usuario_id:
            usuario = Usuario.objects.get(id = usuario_id)
        else:
            usuario = None
        valor = self.cleaned_data['nome']
        if not valor:
            raise ValidationError(
                "Campo obrigatorio!"
            )
        nome = NamesValidations.validate_nome(valor)
        if not nome:
            raise ValidationError(
                "Formato inválido use apenas letras numeros e espaços!"
            )
        if NamesValidations.verify_nome_exist(nome,usuario):
            raise ValidationError(
                "Nome já existe!"
            )
        return nome

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get("senha")
        senha_novamente = cleaned_data.get("senha_novamente")

        if senha != senha_novamente:
            self.add_error("senha", ValidationError("Digite a mesma senha nos campos de senha!"))


class ConfiguracaoForm(forms.ModelForm):
    tempo_min_entre_sorteios = forms.IntegerField(min_value=1, max_value=1440, widget=forms.NumberInput(
        attrs={'class': 'form-control form-control-lg form-control-outlined','autocomplete': "off"}
    ))
    iniciar_sorteio_em = forms.IntegerField(min_value=0, max_value=60, widget=forms.NumberInput(
        attrs={'class': 'form-control form-control-lg form-control-outlined','autocomplete': "off"}
    ))
    liberar_resultado_sorteio_em = forms.ChoiceField(choices=TEMPO_LIBERAR_CHOICES,
                                                     widget=forms.Select(
                                                         attrs={
                                                             'class': "form-select-lg form-control form-control-outlined"}
                                                     )
                                                     )
    
    logo_login = forms.ImageField(required=False, widget=forms.FileInput(
        attrs={'class': "custom-file-input", 'onChange':"document.getElementById('logo_login').src = window.URL.createObjectURL(this.files[0])"}))
    logo_dash = forms.ImageField(required=False, widget=forms.FileInput(
        attrs={'class': "custom-file-input", 'onChange':"document.getElementById('logo_dash').src = window.URL.createObjectURL(this.files[0])"}))
    logo_promo = forms.ImageField(required=False, widget=forms.FileInput(
        attrs={'class': "custom-file-input", 'onChange':"document.getElementById('logo_promo').src = window.URL.createObjectURL(this.files[0])"}))
    favicon = forms.ImageField(required=False, widget=forms.FileInput(
        attrs={'class': "custom-file-input", 'onChange':"document.getElementById('favicon').src = window.URL.createObjectURL(this.files[0])"}))

    nome_server = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-md form-control-outlined" ,'autocomplete': "off"}
    ))
    nome_botao = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-md form-control-outlined" ,'autocomplete': "off"}
    ))
    url_botao = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-md form-control-outlined" ,'autocomplete': "off"}
    ))

    class Meta:
        model = Configuracao
        fields = ['tempo_min_entre_sorteios',
                  'iniciar_sorteio_em',
                  'logo_dash','logo_login','favicon','nome_server','nome_botao','url_botao','logo_promo']


class PartidaEditForm(forms.ModelForm):
    dia_partida = forms.CharField(widget=forms.DateInput(
        attrs={'data-date-format': "dd/mm/yyyy", 'data-provide': "datepicker",
               'class': "form-control form-control-lg form-control-outlined date-picker inputIni inputFim",
               'autocomplete': "off"}),required=False)
    hora_partida = forms.CharField(widget=forms.TimeInput(
        attrs={'type': "time", 'class': "form-control form-control-lg form-control-outlined",
               'autocomplete': "off"}),required=False)
    tipo_rodada = forms.ChoiceField(
        widget=forms.Select(attrs={'class': "form-select-lg form-control form-control-outlined", 'autocomplete': "off"}),
        choices=PARTIDA_TIPOS_CHOICES, required=False)
    nome_sorteio = forms.CharField(
        widget=forms.TextInput(attrs={'class':"form-control form-control-lg form-control-outlined", 'maxlength': "17",
                                     'autocomplete': "off"}), required=False)
    valor_kuadra = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off",
               'type': "number"}), required=False)
    valor_kina = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off",
               'type': "number"}), required=False)
    valor_keno = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off",
               'type': "number"}), required=False)
    hora_virada = forms.TimeField(required=False,widget=forms.TimeInput(
        attrs={'type': "time", 'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))

    class Meta:
        model = Partida
        fields = ['tipo_rodada', 'nome_sorteio','valor_kuadra','valor_kina',
                  'valor_keno']

    def clean_dia_partida(self):
        data = self.cleaned_data['dia_partida']
        if not data:
            raise ValidationError("Campo obrigatorio!")
        return data

    def clean_hora_partida(self):
        hora = self.cleaned_data['hora_partida']
        if not hora:
            raise ValidationError("Campo obrigatorio!")
        return hora


    def clean_valor_kuadra(self):
        kuadra = self.cleaned_data['valor_kuadra']
        if not kuadra:
            raise ValidationError("Campo obrigatorio!")
        return kuadra

    def clean_valor_kina(self):
        kina = self.cleaned_data['valor_kina']
        if not kina:
            raise ValidationError("Campo obrigatorio!")
        else:
            p = self.instance
        return kina

    def clean_valor_keno(self):
        keno = self.cleaned_data['valor_keno']
        if not keno:
            raise ValidationError("Campo obrigatorio!")
        else:
            p = self.instance
        return keno


    def clean(self):
        cleaned_data = super().clean()
        kuadra = cleaned_data.get("valor_kuadra")
        kina = cleaned_data.get("valor_kina")
        keno = cleaned_data.get("valor_keno")
        data = cleaned_data.get("dia_partida")
        hora = cleaned_data.get("hora_partida")
        dataValor = None
        if data and hora:
            dataValor = data + " " + hora
            dataValor = datetime.datetime.strptime(dataValor, "%d/%m/%Y %H:%M")
        data_atual = datetime.datetime.now()

        if Partida.objects.filter(
                data_partida=dataValor,
        ).exclude(id=self.instance.id).exists():
            raise ValidationError(
                "Já existe uma partida agendada para essa data"
            )
        partida_anterior = Partida.objects.filter(data_partida__lt=dataValor, ).order_by(
            '-data_partida').first()
        partida_posterior = Partida.objects.filter(data_partida__gt=dataValor,).order_by(
            'data_partida').first()
        if partida_anterior or partida_posterior:
            configuracao = Configuracao.objects.last()
            mais_proxima_anterior = partida_anterior.data_partida if partida_anterior else None
            mais_proxima_posterior = partida_posterior.data_partida if partida_posterior else None
            diferenca = None
            diferenca_depois = None
            diferenca_antes = None
            if mais_proxima_anterior:
                diferenca = dataValor - mais_proxima_anterior
                diferenca_antes = diferenca
            if mais_proxima_posterior:
                diferenca_depois = mais_proxima_posterior - dataValor
                if diferenca_antes:
                    diferenca = min([diferenca_antes, diferenca_depois])
                else:
                    diferenca = diferenca_depois
            if diferenca.total_seconds() < (configuracao.tempo_min_entre_sorteios * 60):
                msg = "Existe uma partida agendada próxima as "
                if diferenca == diferenca_depois:
                    msg += mais_proxima_posterior.strftime("%d/%m/%Y %H:%M:%S")
                    msg += ". O próximo horário disponível é as "
                    msg += testa_horario(mais_proxima_posterior).strftime(
                        "%d/%m/%Y %H:%M:%S")
                elif diferenca == diferenca_antes:
                    msg += mais_proxima_anterior.strftime("%d/%m/%Y %H:%M:%S")
                    msg += ". O próximo horário disponível é as "
                    msg += testa_horario(mais_proxima_anterior).strftime(
                        "%d/%m/%Y %H:%M:%S")

                raise ValidationError(msg)

        if data_atual and dataValor and data_atual > dataValor:
            raise ValidationError(
                "A partida precisa possuir uma data e hora maior do que a data e hora atual."
            )

        if keno and kina and keno < kina:
            raise ValidationError(
                "O valor do Keno deve ser maior que o valor da Kina!"
            )

        if kina and kuadra and kina < kuadra:
            raise ValidationError(
                "O valor do Kina deve ser maior que o valor da Kuadra!"
            )


class TemplateEditForm(forms.ModelForm):
    dia_partida = forms.CharField(widget=forms.DateInput(
        attrs={'data-date-format': "dd/mm/yyyy", 'data-provide': "datepicker",
               'class': "form-control form-control-lg form-control-outlined date-picker inputIni inputFim",
               'autocomplete': "off"}),required=False)
    hora_partida = forms.CharField(widget=forms.TimeInput(
        attrs={'type': "time", 'class': "form-control form-control-lg form-control-outlined",
               'autocomplete': "off"}),required=False)
    tipo_rodada = forms.ChoiceField(
        widget=forms.Select(attrs={'class': "form-select-lg form-control form-control-outlined", 'autocomplete': "off"}),
        choices=PARTIDA_TIPOS_CHOICES, required=False)
    valor_kuadra = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off",
               'type': "number"}), required=False)
    valor_kina = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off",
               'type': "number"}), required=False)
    valor_keno = forms.DecimalField(widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off",
               'type': "number"}), required=False)
    class Meta:
        model = TemplatePartida
        fields = ['tipo_rodada','valor_kuadra','valor_kina','valor_keno']

    def clean_dia_partida(self):
        data = self.cleaned_data['dia_partida']
        if not data:
            raise ValidationError("Campo obrigatorio!")
        return data

    def clean_hora_partida(self):
        hora = self.cleaned_data['hora_partida']
        if not hora:
            raise ValidationError("Campo obrigatorio!")
        return hora



    def clean(self):
        cleaned_data = super().clean()
        kuadra = cleaned_data.get("valor_kuadra")
        kina = cleaned_data.get("valor_kina")
        keno = cleaned_data.get("valor_keno")
        data = cleaned_data.get("dia_partida")
        hora = cleaned_data.get("hora_partida")
        data_partida = None
        if data and hora:
            data_partida = data + " " + hora
            data_partida = datetime.datetime.strptime(data_partida, "%d/%m/%Y %H:%M")
        data_atual = datetime.datetime.now()

        if data_atual and data_partida and data_atual > data_partida:
            raise ValidationError(
                "A partida precisa possuir uma data e hora maior do que a data e hora atual."
            )

        if keno and kina and keno < kina:
            raise ValidationError(
                "O valor do Keno deve ser maior que o valor da Kina!"
            )

        if kina and kuadra and kina < kuadra:
            raise ValidationError(
                "O valor do Kina deve ser maior que o valor da Kuadra!"
            )



class CartelasFilterForm(forms.Form):
    partida = forms.IntegerField(required=False,widget=forms.NumberInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    hash = forms.CharField(required=False,widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    codigo = forms.CharField(required=False,widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}))
    resgatada = forms.ChoiceField(
        widget=forms.Select(attrs={'class': "form-control form-control-lg form-control-outlined", 'autocomplete': "off"}),
        choices=StatusCartelaChoice.choices, required=False)