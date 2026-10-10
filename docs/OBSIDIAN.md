# Obsidian: Bases, callouts e revisão

O vault é uma pasta de Markdown. Obsidian é a interface de revisão: tabela de
triagem, clique em `[[wikilink]]`, busca. Nenhum plugin é necessário. Bases
(`.base`) exigem Obsidian 1.9 ou mais recente.

## Começar

1. Copie `vault-template/` para onde quiser (`cp -r vault-template ~/meu-vault`).
2. Abra essa pasta no Obsidian como vault.
3. Aponte `GV_VAULT` para ela (`.env` ou variável de ambiente).
4. Se mudar a taxonomia em `config/categorias.yaml`, renomeie as pastas de
   categoria para bater com as chaves. `transcrever.py` cria as que faltam.

Se o vault for também um repositório git (recomendado: é o seu backup), ignore
`.obsidian/workspace*.json` e nada mais.

## A sessão de revisão semanal

Abra `01-BASES/_triagem.base`. Ela lista tudo em `00-INBOX/` com as colunas de
decisão: data, duração, marcador final, categoria sugerida, qualidade da
transcrição, `categoria`, `manter-audio`.

Para cada linha:

1. Leia o resumo no callout (ou ouça o stamp do áudio, se a transcrição estiver ruim).
2. Preencha `categoria` (uma das pastas) e `manter-audio` (`true`, `false`,
   `re-transcrever`). Dá para editar direto na tabela.
3. Mova a nota para a pasta da categoria (arrastar no explorador de arquivos
   do Obsidian; wikilinks continuam válidos porque o nome não muda).
4. Depois, em `RECORD/<dia>/transcrito/`: `false` → apagar o WAV; `true` →
   mover para seu arquivo de áudio; `re-transcrever` → mover de volta para
   `RECORD/<dia>/` e rodar `transcrever-gradual.py` com modelo maior.

Regra 5 do protocolo: não apague durante a sessão. Marque e apague em outra passagem.

## Bases incluídas

| Base | Mostra |
|---|---|
| `_triagem.base` | notas em `00-INBOX/` com colunas de decisão |
| `_global.base` | todas as notas com tag `gravador`; segunda vista: sem categoria |
| `_conexoes-revisao.base` | relatórios `tipo: conexoes` em `_conexoes/` |
| `_temas-recorrentes.base` | relatórios `tipo: temas` e `tipo: rodada` |
| `_notas-sem-conexao.base` | notas que ainda não receberam bloco de conexões |
| `_tags-a-revisar.base` | tags atuais ao lado das palavras-chave do LLM, para consolidar |

As Bases foram recriadas a partir do que os scripts escrevem; confira ao abrir e
ajuste à sua versão do Obsidian.

## Callouts

Tudo que os scripts escrevem no corpo da nota é um callout recolhido (`-`),
acima de `## Transcrição`:

- `> [!<tipo>]- Análise <Fonte> · <CATEGORIA>` — um por nota, de `enriquecer.py`.
  O tipo vem de `callout:` no YAML. A fonte é `Ollama` ou `Gemini`.
- `> [!warning] Coesão: …` — logo abaixo, só quando a transcrição veio de um
  modelo rápido e o LLM julgou o texto fragmentado.
- `> [!warning] Transcrição alucinada …` — no lugar da análise, quando o
  pré-filtro barrou a nota. Nada foi enviado ao LLM.
- `> [!info]- Conexões locais` — de `aplicar-conexoes.py`, com `[[links]]` para
  outras notas e o motivo de cada um.

`enriquecer.py --force` remove os callouts de análise e aviso antes de refazer;
não toca no de conexões nem no texto.

## Propriedades

Todas as propriedades geradas por LLM começam com `llm-`, para que fique claro
na tabela o que é inferência e o que é decisão sua. A lista completa está em
`docs/ARQUITETURA.md`.

Em Bases, propriedades com hífen entram como `note["llm-resumo"]` em filtros e
fórmulas, e como `llm-resumo` em `order:` e `properties:`.

## Migrar um vault que usava outros nomes

Se suas notas têm propriedades com outro prefixo (por exemplo `gemini-*`), um
`sed` resolve. Faça backup (ou commit) antes:

```bash
cd ~/meu-vault
grep -rl '^gemini-' --include='*.md' . | xargs sed -i 's/^gemini-/llm-/'
```

O título dos callouts antigos (`Análise Gemini · …`) pode ficar: `enriquecer.py`
reconhece qualquer `Análise <Fonte> · ` como análise existente. Depois ajuste as
Bases antigas ou substitua pelas de `vault-template/01-BASES/`.
