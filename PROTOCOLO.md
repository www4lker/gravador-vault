# Protocolo de captura e transcrição

> Este texto é a parte do sistema que vale mais do que o código. Foi escrito
> para um gravador de voz barato e um vault Obsidian, mas nada aqui depende de
> marca ou de software. As categorias citadas (ENTREVISTA, NO-ROLE, …) são as de
> quem escreveu; a sua taxonomia vai em `config/categorias.yaml`.

# Protocolo do Gravador

Este documento governa o uso do gravador. O princípio central é simples: **o custo de revisão cresce com o volume e com a desorganização do momento de captura**. Gravar bem é mais fácil do que organizar mal.

---

## Regras Universais

Estas cinco regras se aplicam a todas as pastas, sem exceção.

### 1. Stamp de abertura

Os primeiros três a cinco segundos de cada arquivo precisam conter: **data abreviada + pasta de destino + tema em uma palavra**. Exemplo: *"Trinta e um de maio, NO-ROLE, dissertação."* Esse stamp é o que torna o arquivo triável sem re-escuta completa. Sem stamp, cada arquivo exige atenção plena na revisão. Com stamp, você ouve cinco segundos e decide.

### 2. Um arquivo, uma ideia

Quando o assunto muda, você para e inicia uma nova gravação. Arquivos longos com múltiplas ideias são arquivos que nunca serão revisados — eles parecem "ricos" mas funcionam como gaveta entulhada. Arquivos curtos e monofocais são navegáveis.

### 3. Revisão em lote

Não revise depois de cada uso. Defina um momento fixo por semana — pode ser sexta à noite, pode ser domingo — e passe por todos os arquivos de uma vez. Ouça o stamp, decida: descarta, mantém como memória de áudio, ou transcreve e integra. A revisão em lote é mais rara e mais deliberada que a captura; não vira fardo se você a respeitar como momento distinto.

### 4. Marcador final de qualidade *(bônus)*

Ao terminar cada gravação, antes de pressionar stop, acrescente uma palavra de triage: **"forte"**, **"raso"** ou **"desenvolver"**. Na revisão, você ouve os primeiros cinco segundos (stamp) e os últimos três (marcador) — e já sabe o que fazer com o arquivo sem ouvir o meio. Isso reduz o tempo de revisão em lote drasticamente.

### 5. Nunca apague durante o lote *(bônus)*

Durante a sessão de revisão, você não apaga nada. Você marca mentalmente (ou em uma lista rápida) o que vai descartar, mas o apagamento físico acontece numa segunda passagem, alguns dias depois. Isso previne que um julgamento apressado dentro da sessão de revisão elimine algo que você vai querer depois. O custo de manter um arquivo ruim por mais uma semana é zero. O custo de apagar algo irreversível é alto.

---

## Nuances por Pasta

### `ENTREVISTA`

> [!warning] Bateria e espaço Antes de qualquer entrevista, verifique bateria e espaço disponível. Faça um teste de dez segundos e ouça o playback. Uma entrevista perdida por falha técnica é inrecuperável.

Esta pasta é a de maior risco e maior valor. O protocolo aqui é mais rigoroso.

**Antes:** Desative o modo VAR/VOR — gravação contínua é mais segura em entrevistas porque o silence-detection pode cortar inícios de fala. Confirme o consentimento verbal no começo da gravação; isso serve como registro.

**Stamp específico:** Iniciais do interlocutor + data. Exemplo: *"Trinta e um de maio, ENTREVISTA, [iniciais]."*

**Durante:** Não interrompa o fluxo para checar se está gravando. Confie no teste pré-entrevista. Interrupções para verificar o aparelho quebram o estado de abertura do interlocutor.

**Depois:** Backup imediato, no mesmo dia. Esta é a única pasta onde o backup não é opcional — é parte do protocolo de encerramento da entrevista.

---

### `INSIGHTS-MEDITACAO`

Esta pasta opera numa janela de tempo estreita. O estado pós-sessão que produz os insights não dura — é substituído rapidamente pelo pensamento discursivo normal.

**Timing:** Grave imediatamente ao final da sessão, antes de abrir qualquer aplicativo, antes de checar o celular, antes de se levantar se possível. Cada minuto de delay é perda de sinal.

**Modo:** Stream of consciousness sem estrutura. Não tente organizar o que está dizendo. Não tente ser claro. A fragmentação e a imprecisão são parte do conteúdo — elas dizem algo sobre o estado que as gerou. Arquivos longos aqui são suspeitos: se está elaborando por mais de dois minutos, já está reconstruindo, não capturando.

**Stamp opcional:** A data e o horário já localizam o arquivo no contexto da prática. Um stamp mínimo como *"pós-sessão, manhã"* é suficiente.

---

### `LENDO-COMENTANDO`

Esta pasta tem dois modos de operação distintos, e misturá-los no mesmo arquivo é um erro.

**Modo A — Reação imediata:** Você está lendo, uma ideia surge, você pausa e fala para o gravador sem interromper o ritmo de leitura. Curto, bruto, sem elaboração. O valor está na reação não processada. Stamp inclui o título da obra.

**Modo B — Leitura comentada:** Você lê a passagem em voz alta, pausa três segundos — esse silêncio é intencional, é o tempo de deixar o trecho repercutir — e então comenta. Esta versão âncora o material de modo diferente da leitura silenciosa: a produção articulatória ativa caminhos de retenção que a leitura interna não ativa. Stamp inclui título + número de página aproximado.

> [!tip] Para quebrar a trava editorial Se você travar antes de comentar — querendo dar um "bom" comentário antes de começar a falar — use uma frase de entrada automática: *"o que me estranha aqui é..."* ou *"isso me faz pensar que..."*. Qualquer coisa que force você a começar antes de estar pronto. O conteúdo real vem atrás.

---

### `NO-ROLE`

Pasta para pensamento em trânsito: bicicleta, caminhada, trajeto.

**Dispositivo:** Gravador no bolso ou preso ao guidão. Se usar fone in-ear, você parece estar em uma ligação — elimina o constrangimento de falar em público.

**Timing de captura:** Inicie a gravação **antes** de a ideia estar completamente formada. O ato de pressionar play e começar a falar força a articulação. Esperar até a ideia estar "pronta" é uma armadilha — ideias em movimento se dissipam com a espera.

**Stamp simplificado:** Contexto de movimento é suficiente. *"Rota, dissertação"* ou *"caminhada, Ligotti"* funcionam. A precisão de data é menos importante aqui porque o valor é o pensamento, não o momento.

**Modo VAR/VOR:** Pode ser útil aqui se o ambiente for muito ruidoso, mas teste antes — em vento ou trânsito intenso, o threshold pode cortar sua fala.

---

### `RECORD`

> [!note] Pasta de quarentena `RECORD` funciona como área de staging — tudo que não tem destino claro no momento da captura vai aqui.

Nenhum arquivo deve permanecer em `RECORD` por mais de um ciclo de revisão. Na sessão de lote, todo arquivo desta pasta ganha destino: migra para a pasta correta ou vai para descarte. Se você não consegue decidir para onde mover, o arquivo provavelmente não serve.

Stamp aqui é ainda mais importante, porque você não sabe ainda a que categoria o arquivo pertence — o stamp é o mínimo de informação que vai ajudar a decidir depois.

---

### `RESENHAS`

Esta é a pasta mais próxima de produção escrita. Pense nela como rascunho falado.

**Estrutura implícita recomendada:** Mesmo que você não siga rigidamente, ter uma sequência mental ajuda — impressão inicial → argumento central → veredito. Não é um roteiro, é uma âncora para não ficar circulando sem sair do lugar.

**Stamp específico:** Suporte (livro / série / filme) + título. Exemplo: *"Trinta e um de maio, RESENHAS, livro, Ligotti, Canções."*

**Múltiplas gravações para uma mesma obra:** Aceitável e produtivo. Uma gravação de reação imediata logo após terminar, outra de revisão dias depois. A distância temporal entre elas frequentemente revela o que ficou e o que evaporou — isso em si é informação crítica sobre a obra.

---

### `SONHEI-ESSA-NOITE`

A janela de captura de sonhos é de minutos. O decaimento é rápido e não linear — algumas cenas somem em trinta segundos, outras resistem por horas, mas você não sabe quais são quais antes que já seja tarde.

**Posicionamento do gravador:** Na cabeceira, ao alcance da mão sem sentar. Antes de dormir, deixe o gravador ligado em modo standby ou com o mínimo de botões entre você e a gravação.

**Técnica de captura:** Grave antes de se mover, antes de sentar, antes de abrir os olhos completamente se possível. O movimento físico acelera a dissolução do estado onírico. Fale as imagens antes de tentar construir narrativa — deixe os fragmentos virem sem tentar conectá-los em tempo real.

> [!tip] Sobre incoerência Uma gravação de sessenta segundos cheia de fragmentos incoerentes é melhor do que uma de cinco minutos começando cinco minutos depois do despertar. Não tente fazer sentido no momento de captura.

**Sem stamp de abertura:** Esta é a única exceção à regra do stamp. No estado de despertar imediato, qualquer protocolo adicional vai custar mais do que vai ajudar. Comece a falar diretamente.

---

## Resumo Operacional

| Pasta | VAR/VOR | Stamp | Timing crítico | Backup imediato |
| :---- | :---- | :---- | :---- | :---- |
| ENTREVISTA | Desligado | Iniciais + data | Pré-gravação | Sim |
| INSIGHTS-MEDITACAO | Indiferente | Mínimo | Pós-sessão imediata | Não |
| LENDO-COMENTANDO | Indiferente | Título + página | Durante/após leitura | Não |
| NO-ROLE | Opcional | Contexto de rota | Antes da ideia terminar | Não |
| RECORD | Indiferente | Obrigatório | Qualquer | Não |
| RESENHAS | Desligado | Suporte + título | Após obra | Não |
| SONHEI-ESSA-NOITE | Indiferente | Nenhum | Antes de se mover | Não |


---

# Parte 2 — Transcrição e integração

## Princípio fundamental

A introdução do Whisper não altera o protocolo do gravador. Ela acrescenta uma camada.

O erro mais comum de quem descobre transcrição automática é imaginar que todo áudio deve virar texto. Isso produz inflação documental: milhares de páginas que jamais serão relidas. O objetivo deste protocolo é impedir que isso aconteça.

Nem tudo que merece ser gravado merece ser transcrito.
Nem tudo que merece ser transcrito merece ser integrado ao vault.
Nem tudo que merece ser integrado merece se tornar texto de trabalho.

Cada etapa é um filtro.

## A cadeia completa

Captura → Revisão em lote → Decisão → Transcrição → Integração → Elaboração

O Whisper entra depois da revisão. A revisão continua sendo o mecanismo principal de seleção: gasta-se poder computacional e atenção humana só nos arquivos que sobreviveram à triagem.

## Três destinos possíveis para um arquivo

1. **Captura apenas.** O áudio permanece áudio. Sonhos fragmentários, reflexões muito pessoais, registros cujo valor está na voz. Pode ser mantido ou descartado depois. Nenhuma transcrição.
2. **Captura + transcrição.** O texto vai para o vault para ficar pesquisável. Caminhadas reflexivas, leituras comentadas, reflexões sobre pesquisa.
3. **Captura + transcrição + elaboração.** O texto passa a participar da produção intelectual: entrevistas, pré-textos, argumentos em desenvolvimento, material para artigos.

## O papel do Whisper

O valor do Whisper não está em transcrições perfeitas, e elas não são. Está em tornar material oral pesquisável, indexável, relacionável a outras notas e recuperável anos depois. A função estratégica é aumentar a recuperabilidade do acervo.

## Escolha de modelo

- **small** — modo operacional padrão para a maior parte dos registros rápidos (NO-ROLE, INSIGHTS-MEDITACAO, LENDO-COMENTANDO). Rápido, leve, permite outros programas abertos. Em 8 GB de RAM sem GPU é o que roda sem atrito.
- **medium** — quando o custo do erro aumenta: ENTREVISTA, material para publicação, muito ruído, vários participantes. Feche o navegador antes.
- **large-v3** — melhor qualidade, mais lento e pesado; vale só em máquina com mais RAM ou GPU e para material de alto valor.

O campo `modelo:` fica no frontmatter de cada nota. Quando a transcrição veio de um modelo rápido, `enriquecer.py` pede ao LLM que avalie a coesão do texto e avisa quando convém re-transcrever (`transcrever-gradual.py`).

## O que o LLM faz e não faz

O LLM local lê a transcrição e produz um resumo estruturado **por tipo de registro**: um sonho não vira resumo (vira lista de fragmentos e afetos); um pré-texto vira premissa, tese, objeção e veredito; uma entrevista vira turnos inferidos e falas do interlocutor. Os esquemas estão em `config/categorias.yaml`.

Ele não decide nada. Sugere categoria, extrai palavras-chave e perguntas abertas, propõe conexões entre notas. Toda escrita no vault acontece em callouts separados, acima da transcrição, e a transcrição nunca é reescrita. Decidir categoria, manter ou apagar o áudio, e aceitar ou não uma conexão continua sendo trabalho humano, na sessão de revisão.
