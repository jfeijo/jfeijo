# Busca de imóveis para alugar — Porto Alegre e Nova Petrópolis

Busca nos portais, filtra pelos nossos critérios, dá uma nota de 0 a 100 para cada imóvel
e gera uma página (`relatorio.html`) com os melhores primeiro, marcando o que é **novo**.

## O que ele procura

**Porto Alegre** — apartamento (ou cobertura / casa em condomínio), **89 m² ou mais**.
- Bairros, em ordem de preferência: **Petrópolis** (perto da Av. Soledade), Bela Vista, Mont'Serrat,
  Boa Vista, Chácara das Pedras, Três Figueiras, Rio Branco, Auxiliadora, Higienópolis,
  Moinhos de Vento, Jardim Botânico e, com peso menor, Passo d'Areia, Cristo Redentor,
  Vila Ipiranga, Jardim Europa, Santa Cecília.
- Qualquer bairro fora dessa lista é descartado (há também uma lista explícita de excluídos).
- Distância da Av. Soledade entra na nota.

**Nova Petrópolis** — casa ou sobrado com 89 m²+, ou apartamento **amplo (120 m²+)**.
Bairros: Pousada da Neve, Centro, Bavária, Vila Olinda, Logradouro, Vila Juriti, Piá, São José.

**Orçamento** — aluguel + condomínio até **R$ 3.500**. Em Porto Alegre, um apto muito bom
(nota ≥ 75) pode ir até **R$ 4.200**.

**A nota considera:** bairro (30), distância da Soledade (15), segurança — portaria 24h, câmeras,
guarita (15), bom estado — reformado, novo, porcelanato (15), espaço extra, vagas, 3 quartos,
e bônus para área verde, academia e lazer. Palavras como "precisa de reforma", "infiltração",
"antigo" tiram pontos. Tudo isso está em [`config.yaml`](config.yaml) e pode ser ajustado.

## Como usar

Precisa de Python 3.10+. Rode no seu computador (os portais bloqueiam servidores na nuvem).

```bash
cd busca-imoveis
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m imoveis buscar      # busca tudo e gera relatorio.html
```

Abra `relatorio.html` no navegador. Rode `buscar` de novo a cada dia ou dois: o que já foi visto
fica guardado em `imoveis.db` e só o que é novo aparece com a etiqueta **NOVO**.

Outros comandos:

```bash
python -m imoveis buscar --fontes zap vivareal          # só algumas fontes
python -m imoveis buscar --cidade nova_petropolis       # só uma cidade
python -m imoveis links                                 # gera links.html
python -m imoveis importar meus_imoveis.csv             # anúncios achados à mão
python -m imoveis marcar 3fa9c1d2 favorito "visitar sábado"
python -m imoveis marcar 3fa9c1d2 descartado            # some do relatório
```

O código de 8 letras aparece no rodapé de cada cartão do relatório.

## Fontes

| Fonte | Como | Observação |
|---|---|---|
| ZAP Imóveis | automático | mesma API que o site usa |
| VivaReal | automático | idem |
| QuintoAndar | automático | lê os dados da página de busca |
| OLX | automático | idem; traz muito anúncio de particular |
| Imovelweb, Wimóveis, Chaves na Mão, Loft, MGF | `links.html` | links prontos por bairro, com filtro de área e preço quando o portal aceita |
| Imobiliárias (Auxiliadora Predial, Foxter, Guarida, Crédito Real, Ducati, Pinotti…) | `links.html` + `meus_imoveis.csv` | muitas anunciam também no ZAP/VivaReal, que já entram no automático |

Achou algo num site de imobiliária ou no Facebook? Coloque uma linha em `meus_imoveis.csv`
(url, cidade, bairro, tipo, area, quartos, vagas, aluguel, condominio, iptu, titulo, descricao)
e rode `importar`: ele recebe a mesma nota e entra no mesmo relatório.

Se um portal mudar o formato ou bloquear, o programa avisa e segue com os outros.
Nesse caso use os links do `links.html` para aquele portal.

## Depois da busca: checklist de visita

- Segurança: portaria 24h de verdade (não só interfone), câmeras, como é a rua à noite.
- Estado: fachada, hall e elevador dizem muito sobre o condomínio; olhe sinais de umidade nos cantos.
- Pergunte o valor exato do condomínio e se há chamada extra prevista.
- Confira a ata da última assembleia (obras, inadimplência).

## Testes

```bash
python -m pytest -q
```
