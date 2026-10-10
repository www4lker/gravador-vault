# Regras para agentes de IA

Este repositório é código. O vault de quem o usa não é. Vale para qualquer agente
(Claude, Codex, Aider, Gemini…) que trabalhe aqui.

## Privacidade, antes de tudo

- As notas do vault são gravações pessoais transcritas. Agentes que rodam em
  serviço remoto não abrem, buscam, copiam, resumem nem citam notas, relatórios de
  `_conexoes/`, caches ou logs que reproduzam esse conteúdo.
- O conteúdo do vault só é processado pelos modelos locais (Ollama, Whisper). A
  saída para a rede (`--fonte gemini`) é opt-in, explícita, e decisão da pessoa,
  nunca do agente.
- Testes usam notas sintéticas. Nunca copie uma nota real, um ID real (o nome do
  WAV é data e hora de uma gravação) ou uma tag real para `tests/`, docs ou
  mensagens de commit. Antes de publicar, rode o `grep` de identificadores de
  [docs/CONTRIBUIR.md](docs/CONTRIBUIR.md).
- Para diagnosticar um problema no vault de alguém, peça contagens, nomes de campo
  e mensagens de erro — não o texto das notas.

## Ao mexer no código

- Tudo que escreve no vault passa por `scripts/comum/notas.py`; caminhos vêm de
  `scripts/comum/config.py`.
- Script que altera notas em lote tem `--dry-run` por padrão e teste próprio.
- Nunca reescreva a seção `## Transcrição`.
- `python3 -m pytest tests -q` verde antes de propor qualquer mudança.
- Demais convenções: [docs/CONTRIBUIR.md](docs/CONTRIBUIR.md).
