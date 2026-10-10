"""Código compartilhado pelos scripts do gravador-vault.

Módulos:
  config      — resolução de caminhos e variáveis GV_* num só lugar
  notas       — leitura/escrita de notas Markdown com frontmatter
  categorias  — taxonomia, prompts e callouts carregados de config/categorias.yaml
  alucinacao  — pré-filtro de transcrições alucinadas pelo Whisper
  llm         — chamadas a Ollama (local) e Gemini CLI (opcional), parse de JSON
  stt         — Faster-Whisper: carregar modelo, transcrever, montar nota
"""
