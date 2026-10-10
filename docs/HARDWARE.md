# Hardware: o que roda em quê

Números de uso real, não de benchmark. Servem para calibrar expectativa.

## O gravador

Um gravador de voz digital de bolso, da faixa de R$ 70 em marketplace, que grava
WAV e nomeia os arquivos por timestamp (`20260602120000.WAV`). Tem modo VAR/VOR
(corta silêncio; desligue em entrevistas). Aparece como pendrive quando ligado
no USB: copiar para `RECORD/` é arrastar.

Por que não o celular: porque o ponto de quem montou isto era caminhar sem
celular. Para quem não tem esse problema, qualquer app de gravação serve; use
`organizar.py --renomear-por-mtime` se os arquivos não vierem com timestamp no
nome. A pipeline não sabe nem precisa saber de onde o áudio veio.

Um microfone de lapela barato melhora bastante entrevistas e leitura em voz
alta. Para pensamento em trânsito o microfone embutido basta.

## As máquinas

| Máquina | CPU / RAM / GPU | O que roda bem | O que não |
|---|---|---|---|
| Notebook | i3 de 13ª geração, 8 GB, sem GPU | Whisper `small` com navegador aberto; `medium` com tudo fechado | `large-v3` (fica inviável); Ollama com modelo ≥ 7 B |
| Desktop (Linux) | Ryzen 5 de 6 núcleos, 16 GB, Radeon RX 6600 | Ollama `qwen3.5:9b` (5,4 GB, 100% na GPU) e `bge-m3`; Whisper `medium` na CPU | Whisper na GPU (CTranslate2 não usa AMD) |
| Mesmo desktop, Windows | idem, com mais disco | Whisper `large-v3` na CPU, lotes grandes à noite | LLM local (não instalado lá) |

Observações:

- **RAM é o gargalo, não CPU.** Whisper `medium` em CPU int8 usa ~2–3 GB;
  `large-v3` ~4–5 GB. Em 8 GB, feche o navegador antes do `medium`.
- **Tempo.** Em CPU de notebook, `small` transcreve ~5–8× mais rápido que
  tempo real; `medium` ~1,5–3×; `large-v3` próximo de tempo real ou pior. Um
  lote de 20 gravações de 5 min com `medium` é coisa de uma hora.
- **LLM local.** Com 16 GB sem swap, um modelo de 9 B quantizado (Q4_K_M) em GPU
  de 8 GB responde a uma nota em 10–40 s. Rodando na CPU, multiplique por 5–10.
  Antes de lotes grandes, feche IDE e navegador.
- **Embeddings** são baratos: `bge-m3` indexa centenas de notas em minutos.

## Modelos usados

| Função | Modelo | Por quê |
|---|---|---|
| Transcrição | Faster-Whisper `small` / `medium` / `large-v3` | CTranslate2: metade da RAM do Whisper original, int8 em CPU |
| Análise por nota | Ollama `qwen3.5:9b` | cabe na GPU de 8 GB; bom em português; precisa de `think: false` |
| Embeddings | Ollama `bge-m3` | multilíngue, dimensão 1024, rápido |
| Fallback em nuvem | Gemini CLI | só para quem não tem máquina para LLM local; o texto sai do computador |

Nada disso é ótimo. São escolhas que coube no hardware disponível. Ver
`LACUNAS.md` para o que vale testar.

## Dual boot

Linux acessa partições NTFS do Windows, então WAVs, repositório e vault podem
ficar num disco compartilhado. Não compartilhe o venv Python nem o cache de
modelos entre sistemas: binários diferentes. Aponte `HF_HOME` para uma pasta
por sistema.
