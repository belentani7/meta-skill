# Meta-Skill 🇧🇷

![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python: stdlib only](https://img.shields.io/badge/python-stdlib_only-blue) ![Dependências: 0](https://img.shields.io/badge/dependencies-0-brightgreen)

> Skill e roteador local, explicável e sem dependências para recomendar tarefas, tiers de modelos e limites de custo.
> [Versión en Español](README.md)

## O que oferece

O Meta-Skill transforma o índice de tarefas e aliases em uma ferramenta testável. Classifica sinais em português, espanhol e inglês; calcula uma **confiança heurística** explicável; abstém-se diante de solicitações ambíguas ou desconhecidas; recomenda um tier; e estima tokens/custo somente quando existem tarifas separadas e aplicáveis ao runtime.

Não executa inferências nem envia o prompt a um provedor. É uma recomendação offline, não um proxy nem uma garantia de qualidade ou economia. Preço ausente aparece como **desconhecido**, nunca como zero.

### Testar o roteador

```bash
python3 meta-skill/scripts/route.py "Build a responsive React component"
python3 meta-skill/scripts/route.py --runtime claude_code --json "Write pytest tests"
printf '%s' "Audite esta API para vulnerabilidades OWASP" \
  | python3 meta-skill/scripts/route.py --json
python3 meta-skill/scripts/route.py --budget 0.10 "Pesquise tendências e cite fontes"
```

Os termos são normalizados sem diferenciar maiúsculas/minúsculas ou acentos e comparados como palavras/frases completas; sinais compartilhados têm menor peso. Sem evidência, o roteador **não** inventa uma categoria nem presume `quick_fix`: solicita revisão e usa o tier padrão.

A pontuação softmax ordena sinais definidos manualmente; **não é uma probabilidade calibrada de acerto**. A estimativa de tokens baseada em caracteres é aproximada, não usa o tokenizer do provedor. Sem preço, contexto ou compatibilidade com o runtime, não se afirma que o orçamento está protegido.

### Testes e avaliação offline

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python meta-skill/scripts/update_models.py --validate
python meta-skill/scripts/evaluate_router.py
```

O avaliador calcula cobertura, accuracy, macro-F1, Brier e erro de calibração (ECE) para dados rotulados. `meta-skill/evaluations/smoke.json` contém exemplos sintéticos e escritos à mão para detectar regressões; **não** representa tráfego real e não sustenta alegações de precisão, probabilidade de sucesso ou economia em produção. Para medir o desempenho real, use dados representativos, consentidos e separados para teste, além de qualidade/preços observados.

### Estimar economia com a sua carga

`estimate_savings.py` compara a política de roteamento por tarefa (incluindo os fallbacks configurados e o limite de custo por solicitação) com um baseline fixo (`premium_reasoning` por padrão, sem fallback). Aceita apenas **dados agregados**; não precisa nem salva prompts. Estima o custo como tokens médios × número de solicitações. Como o fallback depende de cada solicitação, os agregados não reproduzem exatamente o tráfego solicitação por solicitação. Exemplo de estrutura — valores ilustrativos, não medidos:

```json
{
  "observations": [
    {"task_id": "testing", "requests": 1,
     "avg_input_tokens": 500, "avg_output_tokens": 200,
     "max_input_tokens": 800, "max_output_tokens": 400}
  ]
}
```

Salve os agregados fora do repositório e execute:

```bash
python3 meta-skill/scripts/estimate_savings.py \
  --workload /caminho/privado/workload.json --baseline-tier premium_reasoning --json
```

Use `--max-cost 0.10` (USD por solicitação) para testar outro limite; sem essa opção, vale o limite do índice. Se tiver um índice privado com preços, informe-o com `--index /caminho/privado/index-com-precos.json`; os registros devem corresponder exatamente ao alias ativo e conter preços de entrada e saída por 1.000 tokens. Não é necessário salvar esse índice nem a carga de trabalho neste repositório. A ferramenta marca custos que não consegue calcular como desconhecidos. Os campos `max_*` ajudam a conferir se as solicitações observadas cabem no contexto; a soma é conservadora e pode combinar máximos de solicitações distintas. Sem eles, apenas a média é verificada e os extremos permanecem incertos. Economia negativa significa aumento estimado de gasto. O cálculo **não mede qualidade** e não é uma fatura nem uma promessa de economia. O índice incluído ainda não tem preços por modelo; portanto não mostrará economia numérica até que existam preços correspondentes aos aliases ativos e agregados reais.

## Escopo

12 arquétipos expansíveis em `meta-skill/index.json`: segurança, frontend, APIs, DevOps/IaC, dados/ETL, ML/RAG, testes, pequenos ajustes textuais, engenharia de software, pesquisa, escrita/tradução e raciocínio matemático. A classificação ainda é lexical, não semântica: casos incertos ficam para revisão.

Os `fallback` são alternativas, não uma promessa de que um tier é mais barato. O guardião só seleciona uma alternativa quando consegue verificar as tarifas de entrada/saída, o limite definido e a janela de contexto. Sem opção comprovadamente dentro do orçamento, bloqueia a recomendação.

## Instalação da skill

- **Claude Code:** copie `meta-skill/` para `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`).
- **Claude.ai / Cowork:** envie a pasta em Settings → Capabilities, conforme o fluxo disponível na sua conta.

O CLI é executado separadamente, com Python 3.11+ e apenas a biblioteca padrão. Nenhuma instalação de pacote é necessária.

## Atualizar o catálogo

```bash
python3 meta-skill/scripts/update_models.py --validate         # local, sem rede
python3 meta-skill/scripts/update_models.py --dry-run          # prévia
python3 meta-skill/scripts/update_models.py                    # descobre candidatos
python3 meta-skill/scripts/update_models.py --promote-newest   # promoção explícita, sem benchmark
```

O atualizador consulta a lista pública do OpenRouter, normalmente sem API key; se o seu acesso exigir autenticação, lê opcionalmente `OPENROUTER_API_KEY` do ambiente (a chave nunca vai para o índice). Filtra modelos com saída de texto, mantém separados os preços de entrada e saída, preserva dados anteriores quando não há correspondência e grava atomicamente. **Por padrão, os aliases selecionados ficam fixos**: ser mais novo não prova ser melhor. Depois de avaliar uma alternativa, atualize `aliases` manualmente; `--promote-newest` é um atalho opcional sem avaliação de qualidade. `local_zero_token` nunca é atualizado. Veja [o estudo de tendências e as fontes](docs/ROUTING_RESEARCH.md).

O catálogo é uma referência, não uma fatura: cache, imagens, retries, descontos, limites do provedor e tarifas reais de uma CLI podem variar.

## Autor

**BELENTANI** — artista e cantor. Neurodivergente, sem rótulos: vivo isso como um dom. Feito com alma brasileira 🇧🇷 de Barcelona, minha casa.

IG: [@BELENTANI_](https://instagram.com/belentani_)

Licença [MIT](LICENSE).
