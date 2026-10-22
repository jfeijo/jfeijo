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
                area=95, quartos=3, vagas=1, aluguel=3200, condominio=700, lat=-30.0360, lon=-51.1815, pet=True,
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
    assert peso_bairro(POA, "Mont’serrat")[0] == 90
    assert peso_bairro(POA, "Bom Jesus") == (None, True)
    assert peso_bairro(POA, "São João")[1] is True  # enchente 2024


def test_apto_ideal():
    r = avaliar(apto(), CONFIG)
    assert r.aprovado, r.motivos_reprovacao
    assert r.nota >= 75 and r.quadras <= 2
    assert "aceita pet" in r.destaques and "3 quartos" in r.destaques


def test_requisitos_obrigatorios():
    assert not avaliar(apto(area=75), CONFIG).aprovado
    assert not avaliar(apto(quartos=1), CONFIG).aprovado
    assert not avaliar(apto(vagas=0), CONFIG).aprovado
    assert not avaliar(apto(bairro="Menino Deus"), CONFIG).aprovado
    assert avaliar(apto(quartos=2, pet=None), CONFIG).aprovado  # pet é bônus, não obrigatório


def test_orcamento():
    assert not avaliar(apto(aluguel=3300), CONFIG).acima_do_teto          # 4.000
    r = avaliar(apto(aluguel=3500), CONFIG)                               # 4.200: estoura a margem
    assert r.aprovado and r.acima_do_teto
    assert not avaliar(apto(aluguel=3700), CONFIG).aprovado               # 4.400


def test_nova_petropolis():
    casa = Imovel(fonte="t", url="u", cidade="Nova Petrópolis", bairro="Pousada da Neve", tipo="casa",
                  area=130, quartos=3, aluguel=2900, descricao="casa com jardim e churrasqueira")
    assert avaliar(casa, CONFIG).aprovado
    apto_pequeno = Imovel(fonte="t", url="u", cidade="Nova Petrópolis", bairro="Centro", tipo="apartamento",
                          area=95, quartos=2, aluguel=2500, condominio=300)
    assert not avaliar(apto_pequeno, CONFIG).aprovado


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
