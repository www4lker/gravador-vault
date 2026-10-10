# Lacunas, limitações e oportunidades

Este arquivo existe para que ninguém descubra na prática o que já se sabe. Está
dividido em: o que o sistema não faz, o que faz mal, decisões discutíveis que
foram tomadas, e o que vale construir. Quem assumir pode fazer melhor; é
esperado que faça.

## Como este repositório foi feito

A maior parte do código foi escrita por agentes de IA (Claude, Codex) em sessões
dirigidas por uma pessoa sem formação em programação, ao longo de alguns meses
de uso real. O protocolo de captura, a taxonomia, os esquemas de análise por
categoria e todas as decisões de fluxo são da pessoa; a implementação, os testes
e boa parte da documentação são da máquina, revisados em uso. Isso tem duas
consequências práticas:

- O código funciona para o fluxo que foi testado (três máquinas, um gravador,
  um vault com algumas centenas de notas) e não foi exercitado além disso.
- Há convenções de código inconsistentes e pouca engenharia defensiva. Os testes
  cobrem a lógica pura e um fluxo ponta a ponta com um Ollama falso; não cobrem
  Whisper, GPU nem Windows.

## O que não existe

- **Triagem pelo stamp.** O protocolo pede um stamp nos primeiros 5 s ("cinco de
  junho, NO-ROLE, dissertação"). Nada lê esse stamp automaticamente. O caminho
  óbvio: transcrever só os 10 primeiros segundos com o modelo `tiny`, procurar
  no texto uma chave de `categorias.yaml` e preencher `categoria:` já na
  transcrição. Barato, útil, não feito.
- **Diarização.** ENTREVISTA depende do LLM inferir turnos de fala pelo contexto
  textual. Separação real de vozes exige Pyannote ou similar, com modelo gated
  e GPU para ser prático.
- **Monitoramento de pasta.** Nada observa `RECORD/` e dispara transcrição ao
  chegar um arquivo. Tudo é manual, por decisão (o protocolo quer revisão antes
  de transcrever), mas um `watch` opcional seria razoável.
- **Arquivamento dos áudios.** O campo `manter-audio:` é preenchido à mão na
  triagem; mover ou apagar o WAV correspondente também é manual. Um
  `arquivar.py` que lesse esse campo e agisse sobre `RECORD/*/transcrito/` é
  pequeno e não foi escrito.
- **Migração de vault existente.** Quem já tem notas com propriedades de outro
  nome (por exemplo `gemini-*`) precisa renomear à mão ou com `sed`; ver
  `docs/OBSIDIAN.md`.
- **Interface.** Tudo é linha de comando. Não há GUI nem plugin Obsidian.

## O que funciona mal ou com ressalvas

- **Alucinação do Whisper.** Mesmo com `vad_filter` e os limiares anti-alucinação,
  áudio com silêncio longo, vento ou ruído gera frases inventadas. O pré-filtro
  em `comum/alucinacao.py` pega os casos grosseiros (repetição, URLs, baixa
  unicidade); não pega frases plausíveis que nunca foram ditas. Reler a
  transcrição continua necessário para qualquer uso sério.
- **JSON do LLM local.** Modelos de 4–9 B às vezes devolvem JSON inválido ou
  ignoram o esquema. O script salva a resposta bruta num callout de erro e segue.
  Com `format: json` e `think: false` no Ollama a taxa de falha caiu, mas não a zero.
- **Categoria sugerida.** Modelos pequenos erram categoria com frequência,
  principalmente entre NO-ROLE, INSIGHTS-MEDITACAO e PRE-TEXTO. A sugestão é um
  chute informado; a decisão fica na Base de triagem.
- **Conexões entre notas.** O fluxo de embeddings propõe pares por similaridade
  e o LLM comenta. Com poucas notas (menos de ~50) os pares são óbvios ou
  ruidosos; com notas muito genéricas, tudo parece parecido. Os limiares
  (`--min-score 0.72` como "forte") foram calibrados num vault só.
- **ID = nome do arquivo.** Todo o fluxo assume áudios nomeados `YYYYMMDDhhmmss`,
  como gravadores baratos fazem. Para outras fontes há `organizar.py
  --renomear-por-mtime`, que usa a data de modificação; se os arquivos foram
  copiados sem preservar mtime, a data estará errada.
- **Bases do Obsidian.** As `.base` em `vault-template/` foram recriadas a partir
  do que os scripts escrevem, sem o vault original à mão. A sintaxe de Bases
  ainda muda entre versões do Obsidian; confira cada uma ao abrir.
- **Windows.** Os `.bat` funcionam mas foram pouco testados fora de uma máquina.
  `transcrever-gradual.py` usa `msvcrt` no Windows e `termios` no resto; não
  roda em terminais que não sejam TTY.
- **GPU.** `GV_STT_DEVICE=cuda` e `GV_STT_COMPUTE=float16` estão plumbados, mas
  nunca foram testados aqui. Em AMD, o Faster-Whisper (CTranslate2) não usa a
  GPU; só o Ollama usa.
- **Idioma.** Prompts, docs e heurísticas de alucinação são em português. O
  idioma do Whisper é configurável (`GV_IDIOMA`), o resto não.

## Decisões discutíveis

- **Scripts soltos em vez de um pacote instalável.** Não há `pip install`, nem
  CLI única. Cada script é um arquivo que se roda com `python3`. É mais fácil
  de ler e modificar por quem não programa; é pior para distribuir.
- **Só biblioteca padrão para HTTP.** Sem `requests`, sem SDK do Ollama. Menos
  dependências, código um pouco mais verboso.
- **Gemini CLI como provedor opcional.** Mantido para quem não tem máquina para
  LLM local. É nuvem: o texto sai do computador. O padrão é Ollama, e a fonte
  precisa ser pedida explicitamente.
- **Taxonomia em YAML, mas com estrutura fixa.** Dá para mudar categorias,
  prompts, campos e callouts sem tocar em Python. Não dá para mudar a lógica
  (por exemplo, pedir duas chamadas de LLM por nota) sem editar código.
- **Transcrição e LLM no mesmo venv.** Simplifica instalação; o `faster-whisper`
  puxa dependências pesadas que quem só quer conectar notas não precisa.

## Oportunidades, em ordem de retorno sobre esforço

1. `triar.py` (stamp → categoria), descrito acima. Um dia de trabalho.
2. `arquivar.py` (ler `manter-audio`, mover/apagar WAV). Algumas horas.
3. Benchmark reproduzível de modelos de LLM para `enriquecer.py`: 10 notas
   fixas, mesmo prompt, medir JSON válido, tempo e qualidade. Hoje a escolha de
   `qwen3.5:9b` é empírica.
4. Diarização opcional para ENTREVISTA.
5. Transcrição no celular: já existem modelos de fala que rodam em telefones. O
   gravador dedicado continua fazendo sentido para quem quer caminhar sem
   celular, mas a pipeline não deveria se importar de onde vem o áudio, e hoje
   quase não se importa.
6. Empacotar como CLI única (`gv transcrever …`) quando o fluxo estabilizar.
