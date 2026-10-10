# vault-template

Esqueleto mínimo de um vault Obsidian compatível com os scripts. Copie esta
pasta para onde quiser, abra no Obsidian como vault e aponte `GV_VAULT` para ela.

```
00-INBOX/            ← transcrever.py escreve aqui; enriquecer.py lê daqui
01-BASES/            ← tabelas de revisão (.base, Obsidian ≥ 1.9)
_conexoes/           ← relatórios de conectar.py e rodada.py
NO-ROLE/ … /SONHEI-ESSA-NOITE/   ← uma pasta por categoria de config/categorias.yaml
```

Os nomes das pastas de categoria precisam bater com as chaves do
`categorias.yaml`: é pela pasta que `enriquecer.py` infere a categoria de uma
nota. Se você mudar a taxonomia, renomeie as pastas. `transcrever.py` cria as
que faltarem.

As Bases usam propriedades `llm-*` escritas por `enriquecer.py` e `tipo`
escrita nos relatórios. Nenhuma depende de plugin.
