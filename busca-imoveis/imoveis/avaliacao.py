"""Filtros obrigatórios e nota (0–100) de cada imóvel."""
from __future__ import annotations

from dataclasses import dataclass, field

from .modelo import Imovel, distancia_km, normalizar

TIPOS_CASA = {"casa", "sobrado", "casa_condominio"}


@dataclass
class Resultado:
    aprovado: bool
    nota: float = 0.0
    motivos_reprovacao: list[str] = field(default_factory=list)
    destaques: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    distancia_km: float | None = None
    quadras: int | None = None
    acima_do_teto: bool = False


def _cfg_cidade(config: dict, cidade: str) -> dict | None:
    alvo = normalizar(cidade)
    for c in config["cidades"].values():
        if normalizar(c["nome"]) == alvo:
            return c
    return None


def peso_bairro(cfg_cidade: dict, bairro: str) -> tuple[float | None, bool]:
    """Retorna (peso, excluido). Aceita variações: 'Petropolis', 'PETRÓPOLIS', 'Mont’serrat'."""
    b = normalizar(bairro)
    for nome in cfg_cidade.get("bairros_excluidos", []) or []:
        if normalizar(nome) == b:
            return None, True
    melhor = None
    for nome, peso in cfg_cidade["bairros"].items():
        n = normalizar(nome)
        if b == n or (n and f" {n} " in f" {b} "):
            if melhor is None or len(n) > melhor[0]:
                melhor = (len(n), peso)
    return (melhor[1] if melhor else None), False


def _tem(texto: str, termos: list[str]) -> list[str]:
    return [t for t in termos if (tn := normalizar(t)) and f" {tn} " in f" {texto} "]


def avaliar(im: Imovel, config: dict) -> Resultado:
    cfg = _cfg_cidade(config, im.cidade)
    if cfg is None:
        return Resultado(False, motivos_reprovacao=[f"cidade fora da busca: {im.cidade}"])

    motivos, destaques, alertas = [], [], []
    eh_poa = normalizar(cfg["nome"]) == "porto alegre"
    ref = config["referencia"]

    # --- Bairro
    peso, excluido = peso_bairro(cfg, im.bairro)
    if excluido:
        motivos.append(f"bairro excluído: {im.bairro}")
    elif peso is None:
        motivos.append(f"bairro fora da lista: {im.bairro or '?'}")

    # --- Tipo, área, quartos, vaga
    tipo = im.tipo or "apartamento"
    if tipo not in cfg["tipos"]:
        motivos.append(f"tipo não aceito: {tipo}")
    area_min = cfg["area_minima"]
    if tipo == "apartamento" and cfg.get("area_minima_apartamento"):
        area_min = cfg["area_minima_apartamento"]
    if im.area is None:
        alertas.append("área não informada")
    elif im.area < area_min:
        motivos.append(f"área {im.area:.0f} m² < {area_min} m²")
    if im.quartos is not None and im.quartos < cfg.get("quartos_minimo", 1):
        motivos.append(f"{im.quartos} quarto(s)")
    if (im.vagas or 0) < cfg.get("vagas_minimo", 0):
        motivos.append("sem vaga de garagem")

    texto = im.texto_completo()
    pal = config["palavras"]
    seg, bom, ruim = _tem(texto, pal["seguranca"]), _tem(texto, pal["bom_estado"]), _tem(texto, pal["mau_estado"])
    verde, acad, lazer = _tem(texto, pal["area_verde"]), _tem(texto, pal["academia"]), _tem(texto, pal["lazer"])

    # --- Nota
    nota = 0.30 * (peso or 0)                                          # bairro: até 30
    dist = distancia_km(im.lat, im.lon, ref["lat"], ref["lon"])
    quadras = round(dist * 1000 / ref.get("metros_por_quadra", 110)) if dist is not None else None
    if eh_poa:
        if dist is not None:
            nota += max(0.0, 20 * (1 - dist / 3))                      # perto da Yoshi e Maria: até 20
            if quadras is not None and quadras <= 8:
                destaques.append(f"{quadras} quadras da Yoshi e Maria")
        else:
            alertas.append("sem localização no mapa")
    else:
        nota += 10 + (5 if tipo in TIPOS_CASA else 0)

    if im.quartos and im.quartos >= 3:
        nota += 8
        destaques.append(f"{im.quartos} quartos")
    if im.pet:
        nota += 6
        destaques.append("aceita pet")
    elif im.pet is False:
        alertas.append("não aceita pet")
    else:
        alertas.append("pet não informado — perguntar")
    if (im.vagas or 0) >= 2:
        nota += 3
        destaques.append(f"{im.vagas} vagas")
    if im.area:
        nota += min(8, max(0.0, (im.area - area_min) / 40 * 8))     # espaço extra: até 8
    if seg:
        nota += 7
        destaques.append("portaria/segurança")
    if bom:
        nota += 6
        destaques.append("bom estado")
    if ruim:
        nota -= 10
        alertas.append("sinais de desgaste: " + ", ".join(ruim))
    if verde:
        nota += 3
        destaques.append("área verde")
    if acad:
        nota += 3
        destaques.append("academia")
    if lazer:
        nota += min(4, 2 * len(lazer))
        destaques.append("lazer")

    # --- Preço
    acima = False
    total = im.total
    teto = config["orcamento"]["maximo"]
    teto_flex = config["orcamento"].get("teto_flexivel_poa", teto) if eh_poa else teto
    if total is None:
        alertas.append("preço não informado")
    else:
        nota += max(-5, min(5, (teto - total) / teto * 25))
        if im.condominio is None and tipo not in TIPOS_CASA:
            alertas.append("condomínio não informado")
        if im.condominio_inclui_iptu:
            alertas.append("condomínio inclui IPTU")
        if total > teto_flex:
            motivos.append(f"R$ {total:,.0f} acima do orçamento".replace(",", "."))
        elif total > teto:
            acima = True
            alertas.append(f"estoura a margem: R$ {total:,.0f}".replace(",", "."))

    return Resultado(
        aprovado=not motivos, nota=round(max(0.0, min(100.0, nota)), 1),
        motivos_reprovacao=motivos, destaques=destaques, alertas=alertas,
        distancia_km=round(dist, 2) if dist is not None else None, quadras=quadras, acima_do_teto=acima,
    )
