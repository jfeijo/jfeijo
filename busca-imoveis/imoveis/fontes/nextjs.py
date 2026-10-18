"""QuintoAndar e OLX: lê os anúncios embutidos no JSON das páginas de busca (__NEXT_DATA__).

Esses sites mudam o formato com frequência, então a leitura é por "faro":
percorre o JSON inteiro e pega todo objeto que parece um anúncio (tem preço e área ou quartos).
"""
from __future__ import annotations

from urllib.parse import quote

from ..modelo import Imovel, normalizar
from .base import Fonte, extrair_next_data, inteiro, numero

ALIAS = {
    "id": ["id", "listId", "houseId", "listingId"],
    "url": ["url", "link", "href", "friendlyUrl", "permalink"],
    "titulo": ["title", "subject", "name"],
    "descricao": ["description", "body", "shortDescription"],
    "aluguel": ["rent", "rentPrice", "rentValue", "price", "priceValue", "aluguel"],
    "condominio": ["condoPrice", "condominium", "condominiumFee", "condoFee", "monthlyCondoFee", "condominio"],
    "iptu": ["iptu", "iptuPrice", "propertyTax"],
    "area": ["area", "usableArea", "usableAreas", "size", "totalArea", "areaUtil"],
    "quartos": ["bedrooms", "rooms", "bedroomCount", "quartos", "dormitorios"],
    "banheiros": ["bathrooms", "bathroomCount", "banheiros"],
    "vagas": ["parkingSpots", "parkingSpaces", "garageSpaces", "vagas", "garage_spaces"],
    "bairro": ["neighbourhood", "neighborhood", "bairro", "neighbourhoodName"],
    "endereco": ["address", "street", "streetName", "endereco"],
    "tipo": ["type", "houseType", "category", "real_estate_type", "unitType"],
    "comodidades": ["amenities", "installations", "features", "comodidades"],
    "lat": ["lat", "latitude"],
    "lon": ["lon", "lng", "longitude"],
    "fotos": ["photos", "images", "coverImage", "thumbnail", "photo"],
}


def _pegar(obj: dict, campo: str):
    for k in ALIAS[campo]:
        if k in obj and obj[k] not in (None, "", []):
            return obj[k]
    # OLX guarda vários dados em "properties": [{"name": "size", "value": "90m²"}, ...]
    props = obj.get("properties")
    if isinstance(props, list):
        for p in props:
            if isinstance(p, dict) and p.get("name") in ALIAS[campo]:
                return p.get("value")
    loc = obj.get("location") or obj.get("locationDetails") or obj.get("coordinates")
    if isinstance(loc, dict) and campo in ("bairro", "lat", "lon", "endereco"):
        return _pegar(loc, campo) if loc is not obj else None
    return None


def _parece_anuncio(obj: dict) -> bool:
    if not isinstance(obj, dict):
        return False
    tem_preco = _pegar(obj, "aluguel") is not None
    tem_tamanho = _pegar(obj, "area") is not None or _pegar(obj, "quartos") is not None
    tem_ident = _pegar(obj, "id") is not None or _pegar(obj, "url") is not None
    return tem_preco and tem_tamanho and tem_ident


def encontrar_anuncios(dados) -> list[dict]:
    achados, pilha, vistos = [], [dados], set()
    while pilha:
        atual = pilha.pop()
        if id(atual) in vistos:
            continue
        vistos.add(id(atual))
        if isinstance(atual, dict):
            if _parece_anuncio(atual):
                achados.append(atual)
                continue
            pilha.extend(v for v in atual.values() if isinstance(v, (dict, list)))
        elif isinstance(atual, list):
            pilha.extend(v for v in atual if isinstance(v, (dict, list)))
    return achados


def _tipo(valor) -> str:
    t = normalizar(str(valor or ""))
    if "sobrado" in t:
        return "sobrado"
    if "cobertura" in t or "penthouse" in t:
        return "cobertura"
    if "condominio" in t and "casa" in t:
        return "casa_condominio"
    if "casa" in t or "home" in t or "house" in t:
        return "casa"
    return "apartamento"


def _texto(v) -> str:
    if isinstance(v, dict):
        return " ".join(str(x) for x in v.values() if isinstance(x, (str, int)))
    if isinstance(v, list):
        return " ".join(_texto(x) for x in v)
    return str(v or "")


def converter(obj: dict, fonte: str, cidade: str, base_url: str, bairro_padrao: str = "") -> Imovel:
    url = str(_pegar(obj, "url") or "")
    ident = str(_pegar(obj, "id") or "")
    if url and not url.startswith("http"):
        url = base_url.rstrip("/") + "/" + url.lstrip("/")
    if not url and ident and fonte == "quintoandar":
        url = f"https://www.quintoandar.com.br/imovel/{ident}/alugar"
    fotos = _pegar(obj, "fotos")
    if isinstance(fotos, str):
        fotos = [fotos]
    fotos = [f if isinstance(f, str) else str((f or {}).get("url", "")) for f in (fotos or [])][:3]
    iptu = numero(_pegar(obj, "iptu"))
    return Imovel(
        fonte=fonte,
        url=url,
        cidade=cidade,
        bairro=_texto(_pegar(obj, "bairro")) or bairro_padrao,
        endereco=_texto(_pegar(obj, "endereco")),
        tipo=_tipo(_pegar(obj, "tipo")),
        titulo=_texto(_pegar(obj, "titulo")),
        descricao=_texto(_pegar(obj, "descricao")),
        area=numero(_pegar(obj, "area")),
        quartos=inteiro(_pegar(obj, "quartos")),
        banheiros=inteiro(_pegar(obj, "banheiros")),
        vagas=inteiro(_pegar(obj, "vagas")),
        aluguel=numero(_pegar(obj, "aluguel")),
        condominio=numero(_pegar(obj, "condominio")),
        iptu_mensal=iptu,
        comodidades=[_texto(c) for c in (_pegar(obj, "comodidades") or [])] if isinstance(_pegar(obj, "comodidades"), list) else [],
        lat=_coord(_pegar(obj, "lat")),
        lon=_coord(_pegar(obj, "lon")),
        fotos=[f for f in fotos if f],
        id_fonte=ident,
    )


def _coord(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def slug(texto: str) -> str:
    return normalizar(texto).replace(" ", "-")


class QuintoAndar(Fonte):
    nome = "quintoandar"
    base = "https://www.quintoandar.com.br"

    def buscar(self, cidade_cfg: dict, bairro: str, config: dict):
        url = f"{self.base}/alugar/imovel/{slug(bairro)}-{slug(cidade_cfg['nome'])}-rs-brasil"
        html = self.get(url).text
        for obj in encontrar_anuncios(extrair_next_data(html)):
            yield converter(obj, self.nome, cidade_cfg["nome"], self.base, bairro)


class OLX(Fonte):
    nome = "olx"
    base = "https://www.olx.com.br"

    def buscar(self, cidade_cfg: dict, bairro: str, config: dict):
        consulta = quote(f"{bairro} {cidade_cfg['nome']}")
        for pagina in range(1, config.get("paginas_por_busca", 3) + 1):
            url = f"{self.base}/imoveis/aluguel/estado-rs?q={consulta}&o={pagina}"
            html = self.get(url).text
            achados = encontrar_anuncios(extrair_next_data(html))
            for obj in achados:
                yield converter(obj, self.nome, cidade_cfg["nome"], self.base, "")
            if not achados:
                break
