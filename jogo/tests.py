import datetime

import requests
from django.contrib.auth.models import User
from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from requests.auth import HTTPBasicAuth,AuthBase
from rest_framework import status
from rest_framework.test import APITestCase

from jogo.choices import AcaoBonus
from jogo.models import Jogador, Configuracao, Partida, Regra, Usuario, Cartela, CreditoBonus, RegraBonus


class AccountTests(APITestCase):
    def setUp(self) -> None:
        user = User.objects.create_user(username="david",password="123")
        self.usuario = Usuario.objects.create(
            usuario=user,fone="123456678"
        )

        j1user = User.objects.create_user(username="j1",password="123")
        self.j1 = Jogador.objects.create(nome="j1",usuario="j1",usuario_token="ajE=",user=j1user)

        j2user = User.objects.create_user(username="j2", password="123")
        self.j2 = Jogador.objects.create(nome="j2", usuario="j2", usuario_token="ajI=", user=j2user)

        c: Configuracao = Configuracao.objects.create()
        c.max_vitorias_jogador=1
        c.save()

        self.regra = Regra.objects.create(nome="REGRA")
        self.regrabonus = RegraBonus.objects.create(acao=AcaoBonus.CADASTRO,valor=1,url="www.google.com.br")

    def set_credentials(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.j1.usuario_token)

    def criar_partida(self):
        mais_tarde = datetime.datetime.now() + datetime.timedelta(minutes=10)
        return Partida.objects.create(
            data_partida=mais_tarde, tipo_rodada=1, valor_kuadra=1.0, valor_kina=2.0, valor_keno=3.0, regra=self.regra,
            usuario=self.usuario
        )
    def gerar_bilhete(self, partida):
        return Cartela.objects.create(
            jogador=self.j1,nome=self.j1.nome,codigo="1",partida=partida
        )

    def gerar_creditos_bonus(self):
        CreditoBonus.objects.create(
            regra=self.regrabonus,valor=self.regrabonus.valor,jogador=self.j1,indicado=self.j2
        )


    def test_login_ok(self):
        """
        Ensure we can create a new account object.
        """
        url = reverse('api_login')
        data = {'usuario': 'j1',"senha":"123"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_gerar_bilhete_sem_partida(self):
        url = reverse('api_gerar_bilhete')
        self.set_credentials()
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_gerar_bilhete_ok(self):
        url = reverse('api_gerar_bilhete')
        self.set_credentials()
        self.criar_partida()
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_gerar_bilhete_2x(self):
        url = reverse('api_gerar_bilhete')
        self.set_credentials()
        self.criar_partida()
        response1 = self.client.post(url, {}, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        response2 = self.client.post(url, {}, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.json(),response2.json())

    def test_gerar_bilhete_bonus_sem_bonus(self):
        url = reverse('api_gerar_bilhete_bonus')
        self.set_credentials()
        self.criar_partida()
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gerar_bilhete_bonus_sem_cartela_previa(self):
        url = reverse('api_gerar_bilhete_bonus')
        self.set_credentials()
        self.criar_partida()
        self.gerar_creditos_bonus()
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gerar_bilhete_bonus_ok(self):
        url = reverse('api_gerar_bilhete_bonus')
        self.set_credentials()
        partida = self.criar_partida()
        self.gerar_bilhete(partida)
        self.gerar_creditos_bonus()
        self.assertEqual(self.j1.creditos(),1)
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Cartela.objects.filter(jogador=self.j1,partida=partida).count(),2)
        self.assertEqual(self.j1.creditos(), 0)