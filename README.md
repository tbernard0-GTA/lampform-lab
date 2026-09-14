# LampForm Lab

**Do plano à forma: uma demonstração da pesquisa de uma luminária termoformada.**

[Abrir a demonstração pública](https://lampform-lab.spry-owlet-9982.chatgpt.site)

Uma página em português para contar a história do projeto e explorar seus modelos reais. O público pode consultar o estudo; a manutenção e as alterações do repositório são feitas pelo autor, **Thiago Bernardo**.

## O que explorar

- Os quatro STL originais: HAB-2, Mold, Sub-merged body e Push.
- A peça plana, a rede equivalente conformada e o mapa de demanda dos ligamentos.
- A transição didática entre rede plana e conformada.
- As métricas da v0.2 e a influência da ancoragem da borda nas duas peças.
- A história: geometria original → rede de centros → rede de ligamentos → validação experimental.

Os seletores alteram somente a visualização no navegador. Não há cadastro, gravação de dados, edição compartilhada ou execução de cálculos no servidor.

## Abrir localmente

Instale [Node.js](https://nodejs.org/) 22 ou superior. Depois, dê dois cliques em **PLAY-LAMPFORM-LAB.cmd** ou execute:

```powershell
.\run.ps1
```

Abra http://localhost:4173. A demonstração já inclui os dados e o JavaScript compilado, portanto não precisa instalar Python nem dependências para consultar. Feche o terminal para encerrar o servidor.

## Editar a apresentação

```powershell
npm ci
npm run build
npm test
npm start
```

- `dist/index.html`: conteúdo e história.
- `dist/styles.css`: aparência e responsividade.
- `web/app.js`: visualizador Three.js e controles.
- `dist/data/`: cópia de apresentação dos modelos e resultados.
- `scripts/prepare_data.py`: gera os dados da apresentação a partir dos arquivos originais, com a biblioteca padrão do Python.
- `legacy/lampform_lab_v01/`: conteúdo integral do ZIP fornecido, preservado sem alterações.

Após alterar os dados originais intencionalmente, execute `python scripts/prepare_data.py` e `npm test`. A apresentação é estática; o conteúdo de `dist/` pode ser hospedado em um servidor de arquivos. As fontes usam Google Fonts, com fontes locais de fallback. Os modelos e o código do visualizador são servidos pelo próprio app.

## Como interpretar

Os valores medem **demanda geométrica/estrutural de deformação**. Não são deformações reais calibradas do polímero, tensão de von Mises ou FEA termomecânico completo. A posição intermediária do slider é uma interpolação visual; as cores mostram sempre o resultado final de referência.

| Referência v0.2, ancoragem 2,0 | HAB-2 → Mold | Sub-merged → Push |
| --- | ---: | ---: |
| Células | 65 | 65 |
| Nós / ligamentos | 173 / 234 | 173 / 234 |
| Demanda média | 20,26% | 20,77% |
| P95 | 32,85% | 34,63% |
| Máxima | 53,23% | 51,75% |

Fonte: `legacy/lampform_lab_v01/results_v02/summary_v02.json`. A análise de borda consulta os seis resultados registrados nos CSV. Selecionar outra ancoragem não recalcula o modelo nem muda a rede 3D de referência.

## Escopo desta demonstração

A apresentação utiliza os resultados já fornecidos. Os scripts de pesquisa foram preservados, mas não foram reexecutados para publicar esta demonstração. Os testes conferem a integridade da exportação, as métricas e os comprimentos da rede registrada.

O estudo contém uma proposta heurística de gradiente em SVG, ainda sem candidatos STL finais validados. Um gerador de alternativas, otimização de preenchimentos e exportação de novos sólidos pertencem à próxima fase. A interface não apresenta esses recursos como concluídos.

Para reproduzir a pesquisa, veja o README original em `legacy/lampform_lab_v01/README.md`; ele lista as dependências e os scripts das versões 0.1 e 0.2. Execute esses scripts em uma cópia se quiser manter os resultados arquivados intactos.

## Consulta pública

Este repositório é uma vitrine pública do estudo e é mantido pelo autor. Não foram adicionados colaboradores com escrita. Ser público permite visualizar, baixar e criar forks; isso não concede permissão para alterar este repositório. Não foi adicionada uma licença de código aberto nesta publicação.

O Three.js utilizado pela demonstração é distribuído sob licença MIT; os avisos de terceiros são preservados em `dist/THIRD_PARTY_NOTICES.txt`.
