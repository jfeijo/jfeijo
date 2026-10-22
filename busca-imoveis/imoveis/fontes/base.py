"""Coisas comuns às fontes: sessão HTTP, pausa entre requisições, conversão de números."""
from __future__ import annotations

import json
import random
import re
import time

import requests

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]


class FonteIndisponivel(Exception):
    """A fonte bloqueou, mudou o formato ou está fora do ar."""


class Fonte:
    nome = "base"

    def __init__(self, pausa: float = 2.5):
        self.pausa = pausa
        self.sessao = requests.Session()
        self.sessao.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "pt-BR,pt;q=0.9",
        })
        self._ultima = 0.0

    def _esperar(self):
        falta = self.pausa - (time.time() - self._ultima)
        if falta > 0:
            time.sleep(falta + random.random())
        self._ultima = time.time()

    def get(self, url, **kw) -> requests.Response:
        self._esperar()
        try:
            r = self.sessao.get(url, timeout=30, **kw)
        except requests.RequestException as e:
            raise FonteIndisponivel(f"{self.nome}: erro de rede ({e.__class__.__name__})") from e
        if r.status_code in (403, 429):
            raise FonteIndisponivel(f"{self.nome}: bloqueado (HTTP {r.status_code}). Tente mais tarde ou use os links manuais.")
        if r.status_code >= 400:
            raise FonteIndisponivel(f"{self.nome}: HTTP {r.status_code} em {url}")
        return r

    def buscar(self, cidade_cfg: dict, bairro: str, config: dict):
        raise NotImplementedError


def numero(valor) -> float | None:
    """'R$ 3.500,00' -> 3500.0 ; '90 m²' -> 90.0 ; [90] -> 90.0 ; 3500 -> 3500.0"""
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        valor = next((v for v in valor if v not in (None, "")), None)
        return numero(valor)
    if isinstance(valor, dict):
        for k in ("value", "amount", "price", "valor"):
            if k in valor:
                return numero(valor[k])
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor > 0 else None
    s = str(valor)
    m = re.search(r"\d[\d.,]*", s)
    if not m:
        return None
    s = m.group(0)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") >= 1 and len(s.split(".")[-1]) == 3:
        s = s.replace(".", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


def inteiro(valor) -> int | None:
    v = numero(valor)
    return int(v) if v is not None else None


def extrair_next_data(html: str) -> dict:
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise FonteIndisponivel("página sem __NEXT_DATA__ (formato mudou ou bloqueio)")
    return json.loads(m.group(1))
