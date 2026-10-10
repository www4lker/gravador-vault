# Arquitetura

## Visão em uma tela

```
 gravador / celular / qualquer fonte de áudio
        │  copiar arquivos
        ▼
 RECORD/                              (GV_RECORD, fora do git)
   │  organizar.py          → RECORD/YYYY-MM-DD/*.WAV
   │  transcrever.py        → <vault>/00-INBOX/<ID>.md   + move WAV para transcrito/
   │  enriquecer.py         → callout + propriedades llm-* na mesma nota
   ▼
 <vault>/                             (GV_VAULT, repositório/pasta sua, aberto no Obsidian)
   00-INBOX/        ← triagem em tabela (01-BASES/_triagem.base)
   <CATEGORIA>/     ← você move a nota para cá e preenche categoria + manter-audio
   _conexoes/       ← relatórios de conectar.py e rodada.py
        │
        │  indexar.py           → .cache/conexoes/{notas,embeddings}.jsonl
        │  conectar.py          → propostas.json + relatórios revisáveis
        │  aplicar-conexoes.py  → bloco "Conexões locais" nas notas (só com --aplicar)
        ▼
 revisão humana semanal: decidir, mover, apagar ou arquivar o áudio
```

Dois princípios atravessam tudo:

1. **A transcrição nunca é reescrita.** Scripts só escrevem acima de
   `## Transcrição` (callouts) e no frontmatter. O texto do Whisper, por pior
   que seja, é o registro.
2. **Nada automático altera o vault em lote sem dry-run.** `aplicar-conexoes.py`
   e `rodada.py` só gravam com `--aplicar`; `transcrever.py` e `enriquecer.py`
   têm `--dry-run`; `enriquecer.py` não reprocessa sem `--force`.

## Contrato da nota

Uma nota é um arquivo `<ID>.md`, onde `<ID>` é o nome do áudio (`YYYYMMDDhhmmss`).
Esse ID é a chave de tudo: evita duplicatas na transcrição, é o alvo dos
`[[wikilinks]]`, agrupa por dia no `transcrever-gradual.py`.

| Campo | Quem escreve | Observação |
|---|---|---|
| `title`, `date`, `duracao`, `origem`, `modelo` | `transcrever.py` | `origem` é relativa a `RECORD/`, nunca caminho absoluto |
| `categoria`, `manter-audio` | **você**, na triagem | `manter-audio`: `true`, `false` ou `re-transcrever` |
| `marcador-final` | `enriquecer.py` | detectado nas últimas palavras (`forte`/`raso`/`desenvolver`) |
| `llm-qualidade-transcricao` | `enriquecer.py` | `suspeita`, `alucinada`, `vazia`, `timeout`; ausente se ok |
| `llm-palavras-chave`, `llm-resumo`, `llm-perguntas-abertas`, `llm-instrucoes-para-si`, `llm-categoria-sugerida` | `enriquecer.py` | mapeamento em `frontmatter_padrao` do YAML |
| `llm-status-argumento`, `llm-modo-inferido`, … | `enriquecer.py` | por categoria (`frontmatter:` no YAML) |
| `conexoes-locais` | `aplicar-conexoes.py` | data da última aplicação; usado pela Base `_notas-sem-conexao` |
| `tags` | `transcrever.py` (`gravador`, `inbox`) e você | sempre o último campo |

Corpo:

```markdown
> [!tip]- Análise Ollama · NO-ROLE        ← enriquecer.py (um por nota)
> …

> [!info]- Conexões locais                ← aplicar-conexoes.py (um por nota)
> …

## Transcrição

<texto>

---
*Observações:*                            ← espaço seu
```

## Pontos de extensão

| Ponto | Hoje | Como trocar |
|---|---|---|
| Fonte de áudio | arquivos em `RECORD/` nomeados por timestamp | qualquer coisa que produza arquivos; `organizar.py --renomear-por-mtime` para outros nomes; `stt.eh_wav` lista as extensões aceitas |
| Transcrição (STT) | Faster-Whisper, CPU int8 | `comum/stt.py`: `criar_modelo` e `transcrever` são as duas funções a substituir |
| Análise (LLM) | Ollama local via HTTP; Gemini CLI opcional | `comum/llm.py`: `chamar(prompt, fonte)` despacha; adicionar uma fonte = uma função + um ramo |
| Taxonomia e prompts | `config/categorias.yaml` | editar o YAML; `GV_CATEGORIAS` aponta para outro arquivo |
| Destino | pasta Obsidian com Bases | qualquer pasta de Markdown funciona; as Bases são opcionais |

## Módulos compartilhados (`scripts/comum/`)

- `config.py` — resolução de `GV_*` (ambiente > `.env` > padrão). Única fonte de caminhos.
- `notas.py` — frontmatter, `## Transcrição`, inserção de blocos, listagem de IDs, wikilinks.
- `categorias.py` — carrega o YAML; `inferir`, `build_prompt`, `formatar_callout`, `atualizar_frontmatter`.
- `alucinacao.py` — pré-filtro e marcador final.
- `llm.py` — Ollama (`generate`, `embed`, `tags`), Gemini CLI, `extrair_json`.
- `stt.py` — Faster-Whisper, metadados do áudio (duração via PyAV), montagem da nota.

Os scripts em `scripts/` são finos: argparse + orquestração. `rodada.py` importa
`indexar`, `conectar` e `aplicar-conexoes` como módulos.

## Fluxo de conexões em detalhe

1. `indexar.py` lê cada nota (metadados + 3500 chars de transcrição), gera um
   embedding com `bge-m3` e guarda em `.cache/conexoes/`. Incremental por hash.
2. `conectar.py` calcula, para cada par, `0.65 × similaridade normalizada +
   bônus` (palavras-chave comuns, categoria, pasta, termos do resumo, data).
   Pares ≥ 0.72 são "fortes". Os N melhores vão ao LLM só para uma frase de
   justificativa. Saída: `propostas.json` + dois relatórios Markdown.
3. `aplicar-conexoes.py` insere nas notas um callout com os links fortes, após
   validar que cada `[[ID]]` existe. Dry-run por padrão.
4. `rodada.py` encadeia os três com checkpoint, para vaults grandes e noites
   longas.

O Python escolhe candidatos; o LLM só comenta. Isso é deliberado: pedir a um
modelo de 9 B para "achar conexões no vault" é caro e inventa.
