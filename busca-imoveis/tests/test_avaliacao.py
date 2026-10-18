import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from imoveis.avaliacao import avaliar, peso_bairro  # noqa: E402
from imoveis.fontes.base import numero  # noqa: E402
from imoveis.fontes.nextjs import converter, encontrar_anuncios  # noqa: E402
from imoveis.modelo import Imovel  # noqa: E402

CONFIG = yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
POA = CONFIG["cidades"]["porto_alegre"]


def apto(**kw):
    base = dict(fonte="t", url="https://x/1", cidade="Porto Alegre", bairro="Petrópolis", tipo="apartamento",
                area=95, quartos=3, vagas=1, aluguel=2600, condominio=700, lat=-30.038, lon=-51.187,
                descricao="Reformado, portaria 24h, academia, piscina e jardim")
    base.update(kw)
    return Imovel(**base)


def test_numero():
    assert numero("R$ 3.500,00") == 3500
    assert numero("3.500") == 3500
    assert numero("90 m²") == 90
    assert numero([None, "95"]) == 95
    assert numero("") is None


def test_bairro_variacoes():
    assert peso_bairro(POA, "PETROPOLIS")[0] == 100
    assert peso_bairro(POA, "Montserrat")[0] == 85
    assert peso_bairro(POA, "Bom Jesus") == (None, True)
    assert peso_bairro(POA, "Restinga")[1] is True


def test_apto_ideal_aprovado_com_nota_alta():
    r = avaliar(apto(), CONFIG)
    assert r.aprovado, r.motivos_reprovacao
    assert r.nota >= 75
    assert "academia" in r.destaques and "segurança" in r.destaques


def test_reprova_area_pequena_e_bairro_excluido():
    assert not avaliar(apto(area=70), CONFIG).aprovado
    assert not avaliar(apto(bairro="Bom Jesus"), CONFIG).aprovado
    assert not avaliar(apto(bairro="Centro Histórico"), CONFIG).aprovado


def test_flexibiliza_poa_so_se_for_muito_bom():
    assert avaliar(apto(aluguel=3200, condominio=700), CONFIG).aprovado  # 3900, ótimo
    ruim = apto(aluguel=3200, condominio=700, descricao="precisa de reforma", bairro="Cristo Redentor", lat=None, lon=None)
    assert not avaliar(ruim, CONFIG).aprovado
    assert not avaliar(apto(aluguel=4000, condominio=700), CONFIG).aprovado  # 4700 > teto flexível


def test_nova_petropolis():
    casa = Imovel(fonte="t", url="u", cidade="Nova Petrópolis", bairro="Pousada da Neve", tipo="casa",
                  area=130, quartos=3, aluguel=2900, descricao="casa com jardim e churrasqueira")
    assert avaliar(casa, CONFIG).aprovado
    apto_pequeno = Imovel(fonte="t", url="u", cidade="Nova Petrópolis", bairro="Centro", tipo="apartamento",
                          area=95, aluguel=2500, condominio=300)
    assert not avaliar(apto_pequeno, CONFIG).aprovado  # apto precisa ser amplo
    apto_amplo = Imovel(fonte="t", url="u", cidade="Nova Petrópolis", bairro="Centro", tipo="apartamento",
                        area=140, aluguel=2800, condominio=400)
    assert avaliar(apto_amplo, CONFIG).aprovado
    caro = Imovel(fonte="t", url="u", cidade="Nova Petrópolis", bairro="Centro", tipo="casa", area=150,
                  aluguel=3700, descricao="reformado portaria 24h academia piscina jardim")
    assert not avaliar(caro, CONFIG).aprovado  # flexibilidade só vale em POA


def test_extrator_nextjs():
    dados = {"props": {"pageProps": {"x": [{"lista": [
        {"id": 77, "rent": 2800, "condoPrice": 650, "area": 98, "bedrooms": 3, "neighbourhood": "Bela Vista",
         "type": "Apartamento", "amenities": ["Academia"]},
        {"listId": 5, "url": "/d/apto-1", "price": "R$ 3.100", "subject": "Apto 3 dorm",
         "properties": [{"name": "size", "value": "92m²"}, {"name": "rooms", "value": "3"}]},
    ]}]}}}
    achados = encontrar_anuncios(dados)
    assert len(achados) == 2
    qa = converter(next(a for a in achados if a.get("id") == 77), "quintoandar", "Porto Alegre", "https://q")
    assert qa.url.endswith("/imovel/77/alugar") and qa.total == 3450 and qa.bairro == "Bela Vista"
    olx = converter(next(a for a in achados if a.get("listId") == 5), "olx", "Porto Alegre", "https://www.olx.com.br")
    assert olx.area == 92 and olx.aluguel == 3100 and olx.url == "https://www.olx.com.br/d/apto-1"
