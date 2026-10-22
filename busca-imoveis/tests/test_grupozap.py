from imoveis.fontes.grupozap import Zap, aceita_pet


def test_aceita_pet():
    assert aceita_pet(["PETS_ALLOWED"], "") is True
    assert aceita_pet([], "Apartamento amplo, aceita pet.") is True
    assert aceita_pet([], "Não aceita animais.") is False
    assert aceita_pet([], "Sol da manhã.") is None


def test_converter_preenche_pet_e_vagas():
    item = {
        "listing": {
            "id": "123", "title": "Apto", "description": "", "usableAreas": [90], "bedrooms": [3],
            "parkingSpaces": [1], "unitTypes": ["APARTMENT"], "amenities": ["PETS_ALLOWED"],
            "pricingInfos": [{"businessType": "RENTAL", "price": "3000", "monthlyCondoFee": "700"}],
            "address": {"city": "Porto Alegre", "neighborhood": "Petrópolis", "point": {"lat": -30.03, "lon": -51.18}},
        },
        "link": {"href": "/imovel/123/"},
    }
    im = Zap()._converter(item, "Porto Alegre")
    assert im.pet is True and im.vagas == 1 and im.total == 3700 and im.quartos == 3
