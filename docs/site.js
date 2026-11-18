(() => {
  const button = document.querySelector('[data-copy-url]');
  const status = document.querySelector('.copy-status');
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
  if (!button || !status) return;
  let pending = false;
  button.addEventListener('click', async () => {
    if (pending) return;
    pending = true;
    button.disabled = true;
    const url = button.dataset.copyUrl;
    status.replaceChildren();
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(url);
      status.textContent = 'Enlace copiado al portapapeles.';
    } catch {
      const label = document.createElement('label');
      label.textContent = 'Copia manualmente este enlace: ';
      const field = document.createElement('input');
      field.type = 'text';
      field.readOnly = true;
      field.value = url;
      field.className = 'copy-fallback';
      label.append(field);
      status.append(label);
      field.focus();
      field.select();
    } finally {
      pending = false;
      button.disabled = false;
    }
  });
})();

/* Client-side demonstration. Source categories: meta-skill/index.json */
(() => {
  const tasks = [{"id":"security_audit","tier":"premium_reasoning","keywords":["seguridad","security","auditoria","auditoría","audit","security audit","owasp","vulnerabilidad","vulnerabilidades","vulnerability","vulnerabilities","xss","csrf","pentest","cve","exploit","injection","inyeccion","inyección","brecha de seguridad","security breach","vazamento","vulnerabilidade"]},{"id":"frontend_ui","tier":"standard_coding","keywords":["react","css","tailwind","frontend","front end","componente","component","ui","ux","responsive","responsivo","responsiva","responsiveness","animacion","animación","animation","html","acessibilidade","accesibilidad","accessibility","interface","interfaz","design system"]},{"id":"backend_api","tier":"standard_coding","keywords":["api","rest","graphql","backend","back end","fastapi","express","jwt","oauth","endpoint","swagger","servidor","server","authentication","autenticacion","autenticación","routes","rotas","database api"]},{"id":"devops_iac","tier":"standard_coding","keywords":["docker","kubernetes","terraform","aws","azure","pipeline","ci/cd","deploy","deployment","despliegue","helm","actions","github actions","infraestructura","infrastructure","infraestrutura","devops","continuous integration","integracion continua","integração contínua"]},{"id":"data_etl","tier":"standard_coding","keywords":["etl","pipeline","datos","data","pandas","spark","airflow","dbt","sql","csv","transformacion","transformación","transform","data pipeline","warehouse","data warehouse","dados","consulta sql"]},{"id":"ml_rag","tier":"premium_reasoning","keywords":["rag","langchain","vector","vector database","embeddings","llm","chromadb","pinecone","ia","agente","agentes","mcp","retrieval","recuperacion aumentada","generacion aumentada","generación aumentada","fine tuning","fine-tuning","machine learning","aprendizaje automatico","aprendizaje automático"]},{"id":"testing","tier":"budget_fast","keywords":["testing","test","tests","teste","testes","pytest","playwright","unit","unit tests","e2e","coverage","mock","mocks","prueba","pruebas","test unitario","testes unitarios","integration test","integration tests","integracion tests","integração tests","unitario","unitarios","unitária","unit test"]},{"id":"quick_fix","tier":"local_zero_token","keywords":["typo","typos","errata","spelling","misspelling","whitespace","formatting","format","corrige","corrija","rename variable","punctuation","accent mark","acentos","correct a typo"]},{"id":"software_engineering","tier":"standard_coding","keywords":["programar","programacao","programação","programming","software","codigo","código","code","codebase","coding","refactor","refactoring","implement","implementation","desarrollo","development","repository","repositorio","repo","funcionalidad","feature","code review","revisión de código","revisao de codigo","revisão de código"]},{"id":"research_analysis","tier":"premium_reasoning","keywords":["investigacion","investigación","research","pesquisa","buscar fuentes","fuentes","sources","citation","citations","cita","citar","referencias","references","tendencia","tendencias","trend","trends","benchmark","evidence","evidencia","analisis","análisis","analysis","analizar","study","estudiar","comparar","comparison","compare","comparacao","comparación","comparação","deep research","investiga","investigate","estudo","studies","pesquisar"]},{"id":"writing_translation","tier":"budget_fast","keywords":["redactar","redaccion","redacción","writing","copywriting","traduccion","traducción","traducir","translate","translation","resumir","resumen","summarize","summary","texto","content","contenido","localizar","localization","proofread","correccion de estilo","corrección de estilo","documentation","documentacion","documentación","documentacao","documentação","traduza","resumo","escrever","escrita"]},{"id":"math_reasoning","tier":"premium_reasoning","keywords":["matematica","matemática","matematicas","matemáticas","math","algebra","álgebra","calculus","calculo","cálculo","proof","demostracion","demostración","theorem","teorema","razonamiento","reasoning","logical","logica","lógica","probability","probabilidad","probabilidades","statistics","estadistica","estadística","estatistica","estatística","combinatorics","combinatoria","optimization","optimización","probabilidade","matematico","matemático"]}];
  const form = document.getElementById('route-form');
  const input = document.getElementById('route-input');
  const output = document.getElementById('route-output');
  const example = document.getElementById('route-example');
  if (!form || !input || !output) return;
  const clean = (text) => String(text || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
  function classify(raw) {
    const haystack = ' ' + clean(raw) + ' ';
    const scored = tasks.map(task => {
      const matched = [...new Set(task.keywords.map(clean).filter(Boolean))]
        .filter(word => haystack.includes(' ' + word + ' '));
      const score = matched.reduce((acc, word) => acc + (word.includes(' ') ? 2 : 1), 0);
      return { task, matched, score };
    }).filter(item => item.score > 0).sort((a,b) => b.score - a.score);
    const total = scored.reduce((sum,item) => sum + item.score, 0);
    const first = scored[0];
    const second = scored[1];
    if (!first || (second && (first.score === second.score || (first.score - second.score) / total < .15)) ||
        first.score / total < .55)
      return { id:'Revisión humana', tier:'Sin recomendación', matches:[], abstain:true };
    return { id:first.task.id, tier:first.task.tier, matches:first.matched.slice(0,5), abstain:false };
  }
  form.addEventListener('submit', event => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    const result = classify(text);
    const name = document.createElement('strong');
    name.textContent = result.id.replaceAll('_',' ');
    const tier = document.createElement('span');
    tier.textContent = 'Tier: ' + result.tier;
    const hint = document.createElement('small');
    hint.textContent = result.abstain ? 'Sin evidencia suficiente o señales ambiguas. No se inventa una ruta.' :
      'Señales detectadas: ' + result.matches.join(', ') + '. No se ha ejecutado ningún modelo.';
    output.replaceChildren(name,tier,hint);
  });
  example?.addEventListener('click', () => {
    input.value = 'Audita una API por vulnerabilidades OWASP';
    form.requestSubmit();
  });
})();
