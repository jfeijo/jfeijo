"""Fontes testadas em 22/10/2026: QuintoAndar (API de busca), Guarida (API) e Auxiliadora Predial (dados da página).

ZAP, VivaReal, OLX e Imovelweb bloqueiam servidores na nuvem (Cloudflare). Rodando de casa,
os coletores de grupozap.py / nextjs.py podem funcionar.
"""
from __future__ import annotations

import json
import re

from ..modelo import Imovel, normalizar
from .base import Fonte, FonteIndisponivel, extrair_next_data, inteiro, numero


def _caixa(config: dict) -> dict:
    """Retângulo de busca em volta da Av. Soledade (cobre Petrópolis e vizinhos)."""
    r = config["referencia"]
    raio = config.get("raio_busca_graus", 0.025)
    return {"north": r["lat"] + raio, "south": r["lat"] - raio,
            "east": r["lon"] + raio * 1.15, "west": r["lon"] - raio * 1.15}


def _filtros(config: dict, cidade_cfg: dict) -> dict:
    return {
        "teto": config["orcamento"]["teto_flexivel_poa"],
        "area": cidade_cfg["area_minima"],
        "quartos": cidade_cfg.get("quartos_minimo", 1),
        "vagas": cidade_cfg.get("vagas_minimo", 0),
    }


# ---------------------------------------------------------------- QuintoAndar
PET_QA = "PODE_TER_ANIMAIS_DE_ESTIMACAO"


class QuintoAndarAPI(Fonte):
    nome = "quintoandar"
    por_regiao = True
    url = "https://apigw.prod.quintoandar.com.br/house-listing-search/v2/search/list"

    def buscar(self, cidade_cfg, bairro, config):
        f, cx = _filtros(config, cidade_cfg), _caixa(config)
        ref = config["referencia"]
        headers = {"Content-Type": "application/json", "Origin": "https://www.quintoandar.com.br",
                   "Referer": "https://www.quintoandar.com.br/"}
        offset = 0
        while True:
            corpo = {
                "context": {"mapShowing": False, "listShowing": True, "numPhotos": 12, "isSSR": False},
                "filters": {
                    "businessContext": "RENT",
                    "location": {"coordinate": {"lat": ref["lat"], "lng": ref["lon"]}, "viewport": cx,
                                 "neighborhoods": [], "countryCode": "BR"},
                    # o "total" do QuintoAndar inclui IPTU e seguro: deixa uma folga e recalcula depois
                    "priceRange": [{"costType": "TOTAL_COST", "range": {"max": f["teto"] + 600}}],
                    "specialConditions": [], "excludedSpecialConditions": [],
                    "houseSpecs": {"area": {"range": {"min": f["area"]}}, "houseTypes": [], "amenities": [],
                                   "installations": [], "bathrooms": {"range": {}},
                                   "bedrooms": {"range": {"min": f["quartos"]}},
                                   "parkingSpace": {"range": {"min": f["vagas"]}}, "suites": {"range": {}}},
                    "availability": "ANY", "occupancy": "ANY", "partnerIds": [], "categories": []},
                "sorting": {"criteria": "RELEVANCE", "order": "DESC"},
                "pagination": {"pageSize": 36, "offset": offset},
                "fields": ["id", "rentPrice", "totalCost", "iptuPlusCondominium", "area", "bedrooms", "bathrooms",
                           "parkingSpaces", "address", "neighbourhood", "amenities", "installations", "photos",
                           "coverImage", "type", "location", "isFurnished"],
                "topics": [],
            }
            self._esperar()
            try:
                r = self.sessao.post(self.url, json=corpo, headers=headers, timeout=30)
                r.raise_for_status()
                hits = r.json()["hits"]["hits"]
            except Exception as e:  # noqa: BLE001
                raise FonteIndisponivel(f"quintoandar: {e}") from e
            for h in hits:
                im = self._converter(h["_source"], cidade_cfg["nome"])
                self._detalhar(im)
                yield im
            offset += 36
            if len(hits) < 36 or offset > 2000:
                break

    def _detalhar(self, im: Imovel) -> None:
        """Página do imóvel: aluguel e condomínio separados do IPTU, todas as fotos, descrição, pet."""
        try:
            info = extrair_next_data(self.get(im.url).text)["props"]["pageProps"]["initialState"]["house"]["houseInfo"]
        except Exception:  # noqa: BLE001
            return
        if info.get("rentPrice"):
            im.aluguel = numero(info["rentPrice"])
            im.condominio = numero(info.get("condoPrice")) or 0
            im.iptu_mensal = numero(info.get("iptu"))
            im.condominio_inclui_iptu = False
        if info.get("acceptsPets") is not None:
            im.pet = bool(info["acceptsPets"])
        im.descricao = info.get("remarks") or im.descricao
        fotos = [f.get("url") for f in info.get("photos") or [] if f.get("url")]
        if fotos:
            im.fotos = [f"https://www.quintoandar.com.br/img/med/{f}" for f in fotos][:6]
        im.comodidades += [a.get("key", "") for a in info.get("amenities") or [] if a.get("value") == "SIM"]
        for a in (info.get("condominium") or {}).get("amenities") or []:
            im.comodidades.append(a.get("text") or a.get("key") or "")

    def _converter(self, s: dict, cidade: str) -> Imovel:
        loc = s.get("location") or {}
        fotos = [p["url"] if isinstance(p, dict) else p for p in (s.get("photos") or [])] or [s.get("coverImage")]
        fotos = [f"https://www.quintoandar.com.br/img/med/{f.removeprefix('original')}" for f in fotos if f][:6]
        total = numero(s.get("totalCost"))
        encargos = numero(s.get("iptuPlusCondominium")) or 0
        aluguel = numero(s.get("rentPrice"))
        if aluguel is None and total:
            # total = aluguel + condomínio + IPTU + seguro incêndio (~1,5% do aluguel)
            aluguel = round((total - encargos) / 1.015)
        amen = list(s.get("amenities") or []) + list(s.get("installations") or [])
        tipo = normalizar(s.get("type", ""))
        return Imovel(
            fonte=self.nome,
            url=f"https://www.quintoandar.com.br/imovel/{s['id']}/alugar",
            cidade=cidade,
            bairro=s.get("neighbourhood", ""),
            endereco=(s.get("address") or "").split(" - ")[0],
            tipo="casa" if "casa" in tipo else ("cobertura" if "cobertura" in tipo else "apartamento"),
            titulo=f"{s.get('type', '')} {'mobiliado' if s.get('isFurnished') else ''}".strip(),
            area=numero(s.get("area")), quartos=inteiro(s.get("bedrooms")), banheiros=inteiro(s.get("bathrooms")),
            vagas=inteiro(s.get("parkingSpaces")) or 0,
            aluguel=aluguel,
            condominio=encargos,  # QuintoAndar junta condomínio + IPTU
            condominio_inclui_iptu=True,
            comodidades=amen,
            pet=PET_QA in amen,
            lat=loc.get("lat"), lon=loc.get("lon"),
            fotos=fotos, id_fonte=str(s["id"]),
        )


# ---------------------------------------------------------------- Guarida
class Guarida(Fonte):
    nome = "guarida"
    por_regiao = True
    base = "https://guarida.com.br"
    tipos_ok = {"apartamento", "cobertura", "casa-sobrado", "casa-em-condominio"}

    def _todos(self):
        """A página de busca chama /api/busca-coordenadas com todos os imóveis para alugar no RS."""
        self._esperar()
        try:
            r = self.sessao.post(f"{self.base}/api/busca-coordenadas",
                                 json={"negocio": "alugar", "finalidade": "residencial"},
                                 headers={"Origin": self.base, "Referer": f"{self.base}/busca/alugar"}, timeout=60)
            r.raise_for_status()
            dados = r.json()
            if isinstance(dados, list) and dados:
                return dados
        except Exception:  # noqa: BLE001
            pass
        raise FonteIndisponivel("guarida: API de coordenadas não respondeu (pode exigir navegador)")

    def buscar(self, cidade_cfg, bairro, config):
        f, cx = _filtros(config, cidade_cfg), _caixa(config)
        todos = getattr(self, "_cache", None) or self._todos()
        for i in todos:
            partes = i["url"].split("/")
            if len(partes) < 5 or partes[4] not in self.tipos_ok:
                continue
            if not (cx["south"] < i["latitude"] < cx["north"] and cx["west"] < i["longitude"] < cx["east"]):
                continue
            if not i.get("valor") or i["valor"] > f["teto"]:
                continue
            try:
                html = self.get(self.base + i["url"]).text
                d = extrair_next_data(html)["props"]["pageProps"]["imovel"]
            except Exception:  # noqa: BLE001
                continue
            yield self._converter(d, i["url"], cidade_cfg["nome"])

    def _converter(self, d: dict, url: str, cidade: str) -> Imovel:
        props = {p["slug"]: p.get("valor") for p in d.get("propriedades", [])}
        v = d.get("valores") or {}
        car = (d.get("caracteristicas") or {})
        amen = list(car.get("imovel") or []) + list(car.get("condominio") or [])
        bairro = (d.get("endereco") or "").split(" - ")
        tipo = d.get("tipo", {}).get("slug", "apartamento")
        return Imovel(
            fonte=self.nome, url=self.base + url, cidade=cidade,
            bairro=bairro[1] if len(bairro) > 2 else url.split("/")[3].replace("-porto-alegre-rs", "").replace("-", " ").title(),
            endereco=d.get("logradouro", ""),
            tipo={"casa-sobrado": "sobrado", "casa-em-condominio": "casa_condominio"}.get(tipo, tipo),
            titulo=d.get("titulo", ""), descricao=d.get("descricao", "") or "",
            area=numero(props.get("area")), quartos=inteiro(props.get("dormitorios")),
            banheiros=inteiro(props.get("banheiro")), vagas=inteiro(props.get("vaga")) or 0,
            aluguel=numero(v.get("valor")), condominio=numero(v.get("condominio")), iptu_mensal=numero(v.get("iptu")),
            comodidades=amen, pet="pet" in amen or None,
            lat=numero(d.get("latitude")) and float(d["latitude"]), lon=float(d["longitude"]) if d.get("longitude") else None,
            fotos=[f["url"] for f in (d.get("fotos") or [])][:6], id_fonte=str(d.get("codigo", "")),
        )


# ---------------------------------------------------------------- Auxiliadora Predial
class Auxiliadora(Fonte):
    nome = "auxiliadora"
    base = "https://www.auxiliadorapredial.com.br"

    @staticmethod
    def _rsc(html: str) -> str:
        partes = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
        return json.loads('"' + "".join(partes).replace("\n", "\\n") + '"') if partes else ""

    @staticmethod
    def _ld(texto: str) -> list[dict]:
        itens = []
        for m in re.finditer(r'\{"@context":"https://schema.org".*?(?=\n[0-9a-f]+:|\Z)', texto, re.S):
            try:
                g = json.loads(m.group(0))
            except ValueError:
                continue
            itens += [x for x in g.get("@graph", [g]) if x.get("@type") == "RealEstateListing"]
        return itens

    def buscar(self, cidade_cfg, bairro, config):
        f = _filtros(config, cidade_cfg)
        slug = normalizar(bairro).replace(" ", "-")
        vistos = set()
        for pagina in range(1, config.get("paginas_por_busca", 3) + 1):
            url = f"{self.base}/alugar/residencial/rs+porto-alegre+{slug}?quartos={f['quartos']}&pagina={pagina}"
            novos = 0
            for it in self._ld(self._rsc(self.get(url).text)):
                if it["url"] in vistos:
                    continue
                vistos.add(it["url"])
                novos += 1
                of = (it.get("offers") or [{}])[0]
                acc = of.get("itemOffered") or {}
                area = numero((acc.get("floorSize") or {}).get("value"))
                vagas = next((inteiro(a.get("value")) for a in acc.get("amenityFeature", [])
                              if "Vaga" in a.get("name", "")), 0) or 0
                if (area and area < f["area"]) or vagas < f["vagas"] or (of.get("price") or 0) > f["teto"]:
                    continue
                im = self._detalhe(it["url"], cidade_cfg["nome"], bairro)
                if im:
                    yield im
            if novos == 0:
                break

    def _detalhe(self, url: str, cidade: str, bairro: str) -> Imovel | None:
        try:
            t = self._rsc(self.get(url).text)
        except FonteIndisponivel:
            return None
        it = next(iter(self._ld(t)), None)
        if not it:
            return None
        of = (it.get("offers") or [{}])[0]
        acc = of.get("itemOffered") or {}
        precos = {p.get("name"): p.get("price") for p in (of.get("priceSpecification") or [])}
        if not precos:
            for m in re.finditer(r'"price":(\d+(?:\.\d+)?),"priceCurrency":"BRL","name":"([^"]+)"', t):
                precos.setdefault(m.group(2), float(m.group(1)))
        extras = {p.get("name"): p.get("value") for p in (it.get("additionalProperty") or acc.get("additionalProperty") or [])}
        geo = acc.get("geo") or {}
        cond = re.findall(r'"caracteristica(?:Condominio|Imovel)":\[(.*?)\]', t)
        amen = re.findall(r'"nome":"([^"]+)"', " ".join(cond))
        desc = re.search(r'"descricao":"(.*?)","', t)
        imgs = re.findall(r'https://gestor\.auxiliadorapredial\.com\.br/rest/image/[^"\\ ]+\.(?:jpe?g|png|webp)', t)
        vagas = next((inteiro(a.get("value")) for a in acc.get("amenityFeature", []) if "Vaga" in a.get("name", "")),
                     inteiro(extras.get("Vagas de Garagem"))) or 0
        texto_pet = normalizar(" ".join(amen) + " " + (desc.group(1) if desc else ""))
        return Imovel(
            fonte=self.nome, url=url, cidade=cidade, bairro=bairro,
            endereco=(acc.get("address") or {}).get("streetAddress", ""),
            tipo="apartamento" if "partamento" in acc.get("accommodationCategory", "Apartamento") else "casa",
            titulo=it.get("name", ""), descricao=desc.group(1) if desc else "",
            area=numero((acc.get("floorSize") or {}).get("value")), quartos=inteiro(acc.get("numberOfBedrooms")),
            banheiros=inteiro(acc.get("numberOfBathroomsTotal")), vagas=vagas,
            aluguel=numero(precos.get("Aluguel") or of.get("price")), condominio=numero(precos.get("Condomínio")),
            iptu_mensal=numero(precos.get("IPTU")), comodidades=amen,
            pet=True if ("pet" in texto_pet.split() or "aceita animais" in texto_pet) else None,
            lat=numero(geo.get("latitude")) and float(geo["latitude"]),
            lon=float(geo["longitude"]) if geo.get("longitude") else None,
            fotos=list(dict.fromkeys(imgs))[:6], id_fonte=str(it.get("identifier", "")),
        )
