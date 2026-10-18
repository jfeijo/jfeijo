"""Estrutura de um imóvel e utilidades de texto."""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass, field, asdict


def normalizar(texto: str | None) -> str:
    """Minúsculas, sem acentos, sem pontuação extra. 'Mont’Serrat' -> 'montserrat'."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[’'`´]", "", t)
    t = re.sub(r"[^a-z0-9_]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def distancia_km(lat1, lon1, lat2, lon2) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class Imovel:
    fonte: str                 # zap, vivareal, quintoandar, olx, manual...
    url: str
    cidade: str                # nome como na config ("Porto Alegre")
    bairro: str = ""
    endereco: str = ""
    tipo: str = ""             # apartamento, casa, sobrado, cobertura, casa_condominio
    titulo: str = ""
    descricao: str = ""
    area: float | None = None
    quartos: int | None = None
    banheiros: int | None = None
    vagas: int | None = None
    aluguel: float | None = None
    condominio: float | None = None
    iptu_mensal: float | None = None
    comodidades: list[str] = field(default_factory=list)
    lat: float | None = None
    lon: float | None = None
    fotos: list[str] = field(default_factory=list)
    id_fonte: str = ""

    @property
    def total(self) -> float | None:
        if self.aluguel is None:
            return None
        return self.aluguel + (self.condominio or 0)

    @property
    def chave(self) -> str:
        """Identifica o mesmo imóvel entre execuções (e entre portais quando possível)."""
        if self.id_fonte:
            base = f"{self.fonte}:{self.id_fonte}"
        else:
            base = self.url.split("?")[0].rstrip("/")
        return hashlib.sha1(base.encode()).hexdigest()[:16]

    @property
    def assinatura(self) -> str:
        """Tenta reconhecer o mesmo imóvel anunciado em portais diferentes."""
        area = round(self.area or 0)
        aluguel = round((self.aluguel or 0) / 50) * 50
        return f"{normalizar(self.bairro)}|{area}|{self.quartos}|{aluguel}"

    def texto_completo(self) -> str:
        return normalizar(" ".join([self.titulo, self.descricao, " ".join(self.comodidades)]))

    def para_dict(self) -> dict:
        d = asdict(self)
        d["total"] = self.total
        return d
