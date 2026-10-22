"""ZAP Imóveis e VivaReal (mesmo grupo, mesma API pública usada pelos sites)."""
from __future__ import annotations

from ..modelo import Imovel, normalizar
from .base import Fonte, FonteIndisponivel, inteiro, numero

TIPOS = {
    "APARTMENT": "apartamento",
    "FLAT": "apartamento",
    "PENTHOUSE": "cobertura",
    "HOME": "casa",
    "TWO_STORY_HOUSE": "sobrado",
    "CONDOMINIUM": "casa_condominio",
    "VILLAGE_HOUSE": "casa_condominio",
}
TIPOS_API = {
    "apartamento": ["APARTMENT", "PENTHOUSE"],
    "cobertura": ["PENTHOUSE"],
    "casa": ["HOME"],
    "sobrado": ["TWO_STORY_HOUSE"],
    "casa_condominio": ["CONDOMINIUM"],
}
CAMPOS = (
    "search(result(listings(listing(id,title,description,usableAreas,totalAreas,bedrooms,bathrooms,"
    "parkingSpaces,unitTypes,pricingInfos,address,amenities,updatedAt),link,medias)),totalCount)"
)


def aceita_pet(amenidades: list, descricao: str) -> bool | None:
    """True se o anúncio diz que aceita pet; None quando não informa."""
    if "PETS_ALLOWED" in amenidades:
        return True
    texto = normalizar(descricao)
    if any(t in texto for t in ("nao aceita pet", "nao aceita animais", "proibido animais")):
        return False
    if any(t in texto for t in ("aceita pet", "aceita animais", "pet friendly", "permite pet", "permite animais")):
        return True
    return None


class GrupoZap(Fonte):
    nome = "zap"
    dominio = "www.zapimoveis.com.br"
    api = "https://glue-api.zapimoveis.com.br"
    portal = "zap"
    por_pagina = 30

    def buscar(self, cidade_cfg: dict, bairro: str, config: dict):
        tipos_api = sorted({t for tipo in cidade_cfg["tipos"] for t in TIPOS_API.get(tipo, [])})
        teto = max(config["orcamento"]["maximo"], config["orcamento"].get("teto_flexivel_poa", 0))
        headers = {
            "x-domain": "." + self.dominio.removeprefix("www."),
            "Origin": f"https://{self.dominio}",
            "Referer": f"https://{self.dominio}/",
            "Accept": "application/json",
        }
        for pagina in range(config.get("paginas_por_busca", 3)):
            params = {
                "business": "RENTAL",
                "listingType": "USED",
                "categoryPage": "RESULT",
                "portal": self.portal.upper(),
                "unitTypes": ",".join(tipos_api),
                "usableAreasMin": cidade_cfg["area_minima"],
                "priceMax": int(teto),
                "addressCity": cidade_cfg["nome"],
                "addressState": "Rio Grande do Sul",
                "addressNeighborhood": bairro,
                "size": self.por_pagina,
                "from": pagina * self.por_pagina,
                "page": pagina + 1,
                "includeFields": CAMPOS,
            }
            dados = None
            for versao in ("v2", "v3", "v4"):
                try:
                    r = self.get(f"{self.api}/{versao}/listings", params=params, headers=headers)
                    dados = r.json()
                    break
                except (FonteIndisponivel, ValueError) as e:
                    erro = e
            if dados is None:
                raise FonteIndisponivel(f"{self.nome}: {erro}")
            itens = (((dados.get("search") or {}).get("result") or {}).get("listings")) or []
            for item in itens:
                im = self._converter(item, cidade_cfg["nome"])
                if im:
                    yield im
            if len(itens) < self.por_pagina:
                break

    def _converter(self, item: dict, cidade: str) -> Imovel | None:
        l = item.get("listing") or {}
        if not l:
            return None
        preco = next((p for p in l.get("pricingInfos", []) if p.get("businessType") == "RENTAL"), {})
        end = l.get("address") or {}
        ponto = end.get("point") or {}
        href = ((item.get("link") or {}).get("href")) or ""
        url = href if href.startswith("http") else f"https://{self.dominio}{href}"
        tipo = TIPOS.get((l.get("unitTypes") or [""])[0], "apartamento")
        iptu = numero(preco.get("yearlyIptu"))
        amenidades = list(l.get("amenities") or [])
        return Imovel(
            fonte=self.nome,
            url=url,
            cidade=end.get("city") or cidade,
            bairro=end.get("neighborhood", ""),
            endereco=" ".join(x for x in [end.get("street", ""), str(end.get("streetNumber") or "")] if x).strip(),
            tipo=tipo,
            titulo=l.get("title", ""),
            descricao=l.get("description", ""),
            area=numero(l.get("usableAreas")) or numero(l.get("totalAreas")),
            quartos=inteiro(l.get("bedrooms")),
            banheiros=inteiro(l.get("bathrooms")),
            vagas=inteiro(l.get("parkingSpaces")),
            aluguel=numero(preco.get("price")),
            condominio=numero(preco.get("monthlyCondoFee")),
            iptu_mensal=round(iptu / 12, 2) if iptu else None,
            comodidades=amenidades,
            lat=ponto.get("lat"),
            lon=ponto.get("lon"),
            fotos=[m.get("url", "").replace("{action}", "fit-in").replace("{width}", "640").replace("{height}", "480")
                   for m in (item.get("medias") or [])[:3]],
            id_fonte=str(l.get("id", "")),
            pet=aceita_pet(amenidades, l.get("description", "")),
        )


class Zap(GrupoZap):
    nome = "zap"


class VivaReal(GrupoZap):
    nome = "vivareal"
    dominio = "www.vivareal.com.br"
    api = "https://glue-api.vivareal.com"
    portal = "vivareal"
