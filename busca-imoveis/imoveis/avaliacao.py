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
    acima_do_teto: bool = False


def _cfg_cidade(config: dict, cidade: str) -> dict | None:
    alvo = normalizar(cidade)
    for c in config["cidades"].values():
        if normalizar(c["nome"]) == alvo:
            return c
    return None


def peso_bairro(cfg_cidade: dict, bairro: str) -> tuple[float | None, bool]:
    """Retorna (peso, excluido). Aceita variações: 'Petropolis', 'PETRÓPOLIS', 'Bairro Petrópolis'."""
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
    achados = []
    for t in termos:
        tn = normalizar(t)
        if tn and f" {tn} " in f" {texto} ":
            achados.append(t)
    return achados


def avaliar(im: Imovel, config: dict) -> Resultado:
    cfg = _cfg_cidade(config, im.cidade)
    if cfg is None:
        return Resultado(False, motivos_reprovacao=[f"cidade fora da busca: {im.cidade}"])

    motivos: list[str] = []
    destaques: list[str] = []
    alertas: list[str] = []
    eh_poa = normalizar(cfg["nome"]) == "porto alegre"

    # --- Bairro
    peso, excluido = peso_bairro(cfg, im.bairro)
    if excluido:
        motivos.append(f"bairro excluído: {im.bairro}")
    elif peso is None:
        motivos.append(f"bairro fora da lista: {im.bairro or '?'}")

    # --- Tipo
    tipo = im.tipo or "apartamento"
    if tipo not in cfg["tipos"]:
        motivos.append(f"tipo não aceito: {tipo}")

    # --- Área
    area_min = cfg["area_minima"]
    if tipo == "apartamento" and cfg.get("area_minima_apartamento"):
        area_min = cfg["area_minima_apartamento"]
    if im.area is None:
        alertas.append("área não informada — confirmar")
    elif im.area < area_min:
        motivos.append(f"área {im.area:.0f} m² < {area_min} m²")

    # --- Texto do anúncio
    texto = im.texto_completo()
    pal = config["palavras"]
    seg = _tem(texto, pal["seguranca"])
    bom = _tem(texto, pal["bom_estado"])
    ruim = _tem(texto, pal["mau_estado"])
    verde = _tem(texto, pal["area_verde"])
    acad = _tem(texto, pal["academia"])
    lazer = _tem(texto, pal["lazer"])

    # --- Nota (0–100)
    nota = 0.0
    nota += 0.30 * (peso or 0)                       # bairro: até 30
    dist = distancia_km(im.lat, im.lon, config["referencia"]["lat"], config["referencia"]["lon"])
    if eh_poa:
        if dist is not None:                          # perto da Soledade: até 15
            nota += max(0.0, 15 * (1 - dist / 4))
            if dist <= 1:
                destaques.append(f"{dist:.1f} km da {config['referencia']['nome']}")
        else:
            nota += 15 * (peso or 0) / 100 * 0.6
    else:
        nota += 10                                     # Nova Petrópolis: cidade pequena
        if tipo in TIPOS_CASA:
            nota += 5
            destaques.append(tipo)

    if seg:                                            # segurança: até 15
        nota += min(15, 8 + 3.5 * (len(seg) - 1))
        destaques.append("segurança")
    elif eh_poa:
        alertas.append("anúncio não fala de portaria/segurança")
    else:
        nota += 4  # em casa de Nova Petrópolis é comum não citar

    if bom:                                            # estado: até 15
        nota += min(15, 8 + 3.5 * (len(bom) - 1))
        destaques.append("bom estado")
    if ruim:
        nota -= 10
        alertas.append("sinais de imóvel desgastado: " + ", ".join(ruim))

    if im.area:                                        # espaço extra: até 8
        nota += min(8, max(0.0, (im.area - area_min) / 40 * 8))
    if im.vagas:
        nota += 3 if im.vagas >= 1 else 0
    if im.quartos and im.quartos >= 3:
        nota += 2

    if verde:
        nota += 4
        destaques.append("área verde")
    if acad:
        nota += 4
        destaques.append("academia")
    if lazer:
        nota += min(4, 2 * len(lazer))
        destaques.append("lazer")

    # --- Preço (a decisão de flexibilizar usa a nota antes do ajuste de preço)
    nota_qualidade = nota
    acima = False
    total = im.total
    if total is None:
        alertas.append("preço não informado")
    else:
        teto = config["orcamento"]["maximo"]
        folga = (teto - total) / teto
        nota += max(-10, min(5, folga * 20))           # mais barato = um pouco melhor
        if im.condominio is None and tipo not in TIPOS_CASA:
            alertas.append("condomínio não informado — total pode ser maior")
        if total > teto:
            acima = True
            teto_flex = config["orcamento"].get("teto_flexivel_poa", teto)
            nota_min = config["orcamento"].get("nota_minima_para_flexibilizar", 101)
            if not eh_poa or total > teto_flex or nota_qualidade < nota_min:
                motivos.append(f"total R$ {total:,.0f} acima do orçamento".replace(",", "."))
            else:
                alertas.append(f"passa do teto (R$ {total:,.0f}), mas a nota é alta".replace(",", "."))

    nota = max(0.0, min(100.0, nota))
    return Resultado(
        aprovado=not motivos,
        nota=round(nota, 1),
        motivos_reprovacao=motivos,
        destaques=destaques,
        alertas=alertas,
        distancia_km=round(dist, 2) if dist is not None else None,
        acima_do_teto=acima,
    )
