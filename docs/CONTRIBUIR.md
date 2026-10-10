# Contribuir

Este repositório é mantido por uma pessoa, para uso próprio, e publicado para o
caso de servir a alguém. Não há roadmap nem promessa de resposta rápida. Dito
isso:

## Rodar os testes

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest tests -q
```

Os testes não precisam de Whisper nem de Ollama: `tests/test_e2e.py` sobe um
servidor HTTP falso que imita `/api/generate`, `/api/embed` e `/api/tags`. Se
você mudar o formato das chamadas ao Ollama, atualize o stub também.

Antes de abrir um PR: `python3 -m pytest tests -q` verde e `--help` de cada
script funcionando.

## O que é bem-vindo

- Qualquer item de `LACUNAS.md`, na ordem que estiver lá ou não.
- Relatos de uso em outro hardware, outro gravador, outro idioma, com números.
- Correções nas Bases do Obsidian (foram recriadas sem o vault original).
- Testes para o que hoje não tem (Windows, GPU, Whisper real com áudio curto de fixture).

## O que não será aceito

- Qualquer coisa que edite notas do vault em lote sem `--dry-run` por padrão e
  um flag explícito para gravar.
- Qualquer coisa que reescreva o texto da seção `## Transcrição`.
- Envio de texto para serviços em nuvem como padrão. Nuvem é opt-in explícito.
- Dependências pesadas para ganhos pequenos. O critério é: alguém sem formação
  em programação consegue ler o script e entender o que ele faz?

## Convenções

- Python 3.10+, só biblioteca padrão fora de `faster-whisper`, `av` e `pyyaml`.
- Código, docs e mensagens em português. Nomes de variáveis em português também,
  sem acento.
- Um script = um arquivo em `scripts/`, com docstring de uso no topo e `--help`.
  Lógica compartilhada vai para `scripts/comum/`.
- Tudo que escreve no vault passa por `comum/notas.py`.
- Caminhos vêm de `comum/config.py`. Nunca hardcode um caminho de máquina.

## Se foi um agente de IA que escreveu

Diga no PR. Não é problema; a maior parte do que está aqui foi. Mas quem revisa
precisa saber o que foi rodado de verdade e o que só compilou.
