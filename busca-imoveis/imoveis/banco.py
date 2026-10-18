"""Guarda os imóveis num SQLite local: marca novos, lembra favoritos e descartados."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .modelo import Imovel

ESQUEMA = """
CREATE TABLE IF NOT EXISTS imoveis (
    chave TEXT PRIMARY KEY,
    assinatura TEXT,
    dados TEXT NOT NULL,
    nota REAL,
    aprovado INTEGER,
    avaliacao TEXT,
    primeira_vez TEXT,
    ultima_vez TEXT,
    status TEXT DEFAULT 'novo',      -- novo | visto | favorito | descartado | visitar
    anotacao TEXT DEFAULT ''
);
"""


class Banco:
    def __init__(self, caminho: str | Path):
        self.con = sqlite3.connect(str(caminho))
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)

    def salvar(self, im: Imovel, resultado) -> bool:
        """Salva/atualiza. Retorna True se o imóvel é novo."""
        agora = datetime.now().isoformat(timespec="seconds")
        aval = json.dumps({
            "destaques": resultado.destaques,
            "alertas": resultado.alertas,
            "motivos": resultado.motivos_reprovacao,
            "distancia_km": resultado.distancia_km,
            "acima_do_teto": resultado.acima_do_teto,
        }, ensure_ascii=False)
        existe = self.con.execute("SELECT 1 FROM imoveis WHERE chave=?", (im.chave,)).fetchone()
        if existe:
            self.con.execute(
                "UPDATE imoveis SET dados=?, nota=?, aprovado=?, avaliacao=?, ultima_vez=?, assinatura=? WHERE chave=?",
                (json.dumps(im.para_dict(), ensure_ascii=False), resultado.nota, int(resultado.aprovado),
                 aval, agora, im.assinatura, im.chave),
            )
        else:
            self.con.execute(
                "INSERT INTO imoveis VALUES (?,?,?,?,?,?,?,?,?,?)",
                (im.chave, im.assinatura, json.dumps(im.para_dict(), ensure_ascii=False), resultado.nota,
                 int(resultado.aprovado), aval, agora, agora, "novo", ""),
            )
        self.con.commit()
        return not existe

    def marcar(self, chave: str, status: str, anotacao: str | None = None):
        if anotacao is None:
            self.con.execute("UPDATE imoveis SET status=? WHERE chave LIKE ?", (status, chave + "%"))
        else:
            self.con.execute("UPDATE imoveis SET status=?, anotacao=? WHERE chave LIKE ?",
                             (status, anotacao, chave + "%"))
        self.con.commit()

    def aprovados(self, incluir_descartados=False) -> list[dict]:
        sql = "SELECT * FROM imoveis WHERE aprovado=1"
        if not incluir_descartados:
            sql += " AND status != 'descartado'"
        linhas = self.con.execute(sql + " ORDER BY nota DESC").fetchall()
        saida, vistas = [], set()
        for l in linhas:
            # mesmo imóvel em dois portais: mostra só o de maior nota
            if l["assinatura"] in vistas and not l["assinatura"].endswith("|0|None|0"):
                continue
            vistas.add(l["assinatura"])
            d = dict(l)
            d["dados"] = json.loads(d["dados"])
            d["avaliacao"] = json.loads(d["avaliacao"])
            saida.append(d)
        return saida

    def marcar_vistos(self):
        self.con.execute("UPDATE imoveis SET status='visto' WHERE status='novo'")
        self.con.commit()
