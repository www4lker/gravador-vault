# gravador-vault

Um gravador de voz de R$ 70, um computador comum, modelos locais e um vault
Obsidian. O resultado: pensar falando enquanto caminha e, no fim da semana, ter
uma tabela de tudo que foi dito, com resumo, palavras-chave e links entre ideias.
Clicar num `[[wikilink]]` e chegar até as palavras.

Isto é a infraestrutura mínima para fazer o mesmo, com as lacunas nomeadas.

> **Princípio.** Nem tudo que merece ser gravado merece ser transcrito. Nem
> tudo que merece ser transcrito merece ser integrado ao vault. Cada etapa é um
> filtro, e o filtro é você, numa sessão semanal de revisão. O software só
> prepara a mesa. Leia [PROTOCOLO.md](PROTOCOLO.md) antes do resto.

## O que há aqui

| | |
|---|---|
| [PROTOCOLO.md](PROTOCOLO.md) | Como gravar para que a revisão seja barata: stamp de abertura, um arquivo por ideia, revisão em lote, marcador final. A parte que mais vale. |
| [config/categorias.yaml](config/categorias.yaml) | Tipos de registro e o que pedir ao LLM para cada um. Um sonho não vira resumo; um argumento vira premissa/tese/objeção. Edite para a sua vida. |
| `scripts/` | Oito scripts Python: organizar → transcrever → enriquecer → (indexar → conectar → aplicar). Linha de comando, português, sem framework. |
| `vault-template/` | Esqueleto de vault com as tabelas de revisão (Obsidian Bases). |
| [AGENTS.md](AGENTS.md) | Regras para agentes de IA que trabalhem neste código, a começar pela privacidade do vault. |
| [LACUNAS.md](LACUNAS.md) | O que não funciona, o que funciona mal, decisões discutíveis e o que vale construir. |
| `docs/` | [Arquitetura](docs/ARQUITETURA.md), [hardware](docs/HARDWARE.md), [Obsidian](docs/OBSIDIAN.md), [contribuir](docs/CONTRIBUIR.md). |

## Pipeline

```
gravar  →  copiar WAVs para RECORD/
        →  organizar.py             pastas por dia
        →  transcrever.py           Faster-Whisper → <vault>/00-INBOX/<ID>.md
        →  enriquecer.py            LLM local → callout + propriedades llm-* por categoria
        →  Obsidian: _triagem.base  você decide categoria e destino do áudio
        →  mover a nota; apagar, guardar ou re-transcrever o WAV
        →  (mensal) indexar → conectar → aplicar-conexoes    links entre notas, revisáveis
```

Tudo roda na sua máquina. A única saída para a rede é opcional e explícita
(`--fonte gemini`, para quem não tem hardware para LLM local).

## Instalar

Requisitos: Python 3.10+, [ffmpeg](https://ffmpeg.org/) no PATH, e para análise
e conexões o [Ollama](https://ollama.com/) com dois modelos:

```bash
ollama pull qwen3.5:9b     # análise (qualquer modelo de 7–9 B que siga JSON serve)
ollama pull bge-m3         # embeddings
```

Linux/macOS:

```bash
git clone <este-repo> gravador-vault && cd gravador-vault
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # edite GV_VAULT
cp -r vault-template ~/meu-vault   # e abra no Obsidian
source launchers/gv-env.sh      # define organizar, transcrever, enriquecer, …
transcrever --mostrar-config
```

Windows: `launchers\windows\instalar.bat`, edite `.env`, use `launchers\windows\*.bat`.

Para tornar o `source` permanente, adicione a linha ao `~/.bashrc`.

## Usar

```bash
# depois de copiar os WAVs do gravador para RECORD/
organizar                          # RECORD/2026-06-02/…
transcrever --dry-run              # o que seria transcrito
transcrever RECORD/2026-06-02 --modelo medium
enriquecer                         # analisa tudo em 00-INBOX/ com o Ollama
# → abra o Obsidian, 01-BASES/_triagem.base, decida

# quando o vault tiver algumas dezenas de notas
indexar --limite 30                # teste pequeno
conectar --dry-run
conectar                           # relatórios em <vault>/_conexoes/
aplicar-conexoes                   # dry-run: mostra o que faria
aplicar-conexoes --aplicar         # grava blocos de links nas notas
```

Todo script tem `--help`. Escolha de modelo Whisper: `small` para quase tudo em
máquina de 8 GB; `medium` quando o erro custa (entrevista, publicação);
`large-v3` só com hardware para isso. Detalhes em [docs/HARDWARE.md](docs/HARDWARE.md).

## Honestidade sobre o estado

- Funciona para uma pessoa, em três máquinas, com algumas centenas de notas. Não
  foi testado além disso.
- O Whisper alucina em silêncio e ruído. Há dois filtros; nenhum é suficiente.
- Modelos locais pequenos erram categoria e às vezes devolvem JSON quebrado. O
  sistema degrada com aviso, não com silêncio.
- A maior parte do código foi escrita por agentes de IA sob direção humana. O
  protocolo, a taxonomia e as decisões de fluxo são humanos. Quem assumir deve
  fazer melhor; está tudo em [LACUNAS.md](LACUNAS.md).
- Não é produto. Não há suporte. É compartilhado porque pode servir.
- É um destilado. O sistema de onde saiu continua evoluindo em privado, em outra
  direção (rodadas noturnas, formalização da fala, sínteses), e as duas versões
  não são mantidas em sincronia. O que melhorar lá e servir aqui chega à mão.

## Licença

Código sob MIT. Textos (`PROTOCOLO.md`, `docs/`) sob CC BY-SA 4.0. Ver [LICENSE](LICENSE).

---

## In English

**gravador-vault** is a small, local-first pipeline for turning voice memos
from a cheap recorder (or any audio source) into an Obsidian vault you can
actually review: organize WAVs by day → transcribe with Faster-Whisper →
analyze each note with a local LLM (Ollama) using category-specific prompts →
triage in an Obsidian Base table → optionally link notes by embedding
similarity, with every change reviewable before it is written.

The valuable part is not the code but the capture protocol
([PROTOCOLO.md](PROTOCOLO.md)) and the per-category analysis schemas
([config/categorias.yaml](config/categorias.yaml)): a dream is not summarized,
an argument is decomposed into premise/thesis/objection, an interview gets
inferred speaker turns. Both are in Portuguese, as is the code, the docs and the
Whisper default language (`GV_IDIOMA=pt`, configurable).

Known gaps are listed in [LACUNAS.md](LACUNAS.md). Most of the code was written
by AI agents under human direction and has been used by one person on three
machines. Tests run without Whisper or Ollama (`python3 -m pytest tests`).
This is a distilled snapshot: the private system it came from keeps evolving in
another direction, and the two are not kept in sync. MIT for code, CC BY-SA 4.0 for texts.
