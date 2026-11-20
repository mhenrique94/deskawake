# DeskAwake — Especificação Técnica do Design Visual

**Documento:** `design_visual_aprovado.md`  
**Produto:** DeskAwake  
**Escopo:** identidade do símbolo, indicador de processamento e integração visual na UI GTK3 (E4 / MATE / X11)  
**Status:** **Design visual e animação aprovados** — implementação GTK3 pendente  
**Versão:** 1.0  
**Data:** 2026-11-20

---

## 1. Objetivo e autoridade deste documento

Este documento registra a solução visual aprovada para o símbolo do DeskAwake e sua transformação em indicador de processamento. Seu propósito é orientar implementação sem depender de interpretação estética posterior.

Ele complementa `design_e4.md`. Não substitui `spec.md`, não altera contratos de backend, D-Bus, configuração ou ciclo de vida e não amplia o escopo da entrega E4.

Em caso de conflito:
1. `spec.md` prevalece sobre os documentos de design;
2. `design_e4.md` continua sendo a referência da arquitetura e do comportamento da UI E4;
3. este documento prevalece apenas quanto à forma visual aprovada do símbolo e do indicador de processamento.

**Regra de implementação:** reproduzir os assets aprovados. Não redesenhar, simplificar, “modernizar” ou reinterpretar as formas sem nova aprovação.

## 2. Conceito visual aprovado

O símbolo combina três elementos:

1. **Dois segmentos circulares abertos**, de espessura uniforme e extremidades arredondadas.
2. **Um ponto central**, independente dos segmentos.
3. **Duas pontas de seta sólidas** no estado de processamento, integradas às extremidades dos segmentos.

A forma comunica continuidade, ciclo e atividade. O desenho deve permanecer simples e reconhecível no espaço reduzido de 22 × 22 px.

### 2.1 Estado estático — símbolo-base

- Dois arcos circulares separados por dois vãos.
- Os vãos têm a mesma dimensão.
- Os vãos não são posicionados verticalmente: seus eixos ficam em diagonais opostas, conforme o desenho aprovado.
- O ponto central permanece visualmente independente dos arcos.
- As extremidades dos arcos são arredondadas.
- Não há setas no estado estático.

### 2.2 Estado de processamento — spinner

- Os dois arcos se transformam visualmente em duas setas curvas.
- As pontas são **formas preenchidas e sólidas**, não setas desenhadas com linhas ou contornos.
- Cada ponta é integrada ao respectivo arco: o eixo do arco encontra o centro da base da ponta.
- As setas são equivalentes em forma e dimensão e ficam em posições opostas, preservando a simetria de 180°.
- As pontas avançam para dentro dos vãos diagonais, mas sem eliminar o espaço negativo entre uma ponta e o início do próximo segmento.
- O ponto central continua presente e permanece completamente imóvel durante o processamento.

A referência aprovada é a composição com duas setas curvas opostas, adaptada à inclinação diagonal dos vãos e com o ponto central mantido. Não substituir pela versão convencional com setas pequenas sobrepostas a arcos.

## 3. Geometria e dimensões do asset

O asset é desenhado em uma área quadrada de 22 × 22 unidades, correspondente ao slot de 22 × 22 px da UI E4.

| Propriedade | Valor de referência |
|---|---:|
| `viewBox` | `0 0 22 22` |
| Largura / altura intrínseca | 22 × 22 |
| Centro geométrico | `(11, 11)` |
| Raio do caminho circular | 8 unidades |
| Espessura do corpo dos arcos | 2,2 unidades |
| Raio do ponto central | 1,45 unidades |
| Vãos do símbolo-base | dois, iguais |
| Abertura angular de cada vão | 26° |
| Orientação dos vãos | diagonal, em eixos opostos |
| Simetria | rotação de 180° entre as metades |

As medidas acima descrevem o asset aprovado incluído em `assets/`. O SVG é a fonte geométrica de verdade; não reconstruir os caminhos por aproximação se o arquivo estiver disponível.

### 3.1 Convenções geométricas

- Centro: `(11, 11)`.
- Raio do caminho: `8`.
- O desenho usa `currentColor`, nunca cores de estado codificadas no SVG.
- Os dois arcos do símbolo-base usam o mesmo raio e espessura.
- Os dois vãos têm abertura angular igual e ficam em posições diagonais opostas.
- A segunda metade deve ser equivalente à primeira por rotação de 180°.
- O ponto central é um elemento separado dos caminhos circulares.

### 3.2 Pontas das setas

No spinner:

- A ponta é um polígono preenchido (`fill="currentColor"`).
- Não aplicar `stroke` à ponta.
- A base da ponta é centrada no eixo tangencial do arco correspondente.
- As laterais da ponta partem simetricamente das extremidades da base e convergem para o vértice.
- A forma deve se fundir visualmente ao corpo curvo, sem parecer um triângulo solto ou um ornamento sobreposto.
- As duas pontas usam a mesma geometria, com transformação de 180° entre si.

Não alterar isoladamente o tamanho, a inclinação ou a posição de apenas uma das pontas.

## 4. Cor e comportamento por tema

O símbolo não comunica o estado ON/OFF/ERROR por cor. A cor do símbolo acompanha exclusivamente a cor de texto da variante visual ativa.

| Variante | Cor do símbolo / spinner |
|---|---|
| Claro | `#20252B` |
| Escuro | `#F0F3F5` |

Os SVGs usam `currentColor`. A camada GTK resolve essa cor a partir da variante de tema e injeta o valor no SVG antes da renderização, conforme o mecanismo já previsto em `design_e4.md`.

### 4.1 Regra inviolável: símbolo neutro

O símbolo e o spinner **nunca ficam verdes, cinzas ou vermelhos para representar estado**. Isso inclui o estado ON.

O único indicador cromático de estado é o `Gtk.Switch`:

| Estado público | Cor |
|---|---|
| `on` | `#80D9A4` |
| `off` | `#929DA5` |
| `error` | `#E47F7F` |

As cores são fixas nos temas claro e escuro. Não aplicar essas cores ao SVG, ao ponto central, ao nome ou à superfície do widget.

### 4.2 Superfícies do widget

A especificação visual do widget E4 permanece:

| Variante | Superfície | Texto |
|---|---|---|
| Claro | `#F0F3F5` com opacidade 0,88 quando há compositor | `#20252B` |
| Escuro | `#20252B` | `#F0F3F5` |

Com compositor, manter a superfície translúcida e os cantos arredondados. Sem compositor, usar superfície opaca e fallback de cantos retos, conforme E4. Não usar gradiente ou sombra.

## 5. Integração no widget GTK3 (E4)

O símbolo e o spinner ocupam o mesmo slot visual, sem alterar o layout da pílula.

| Elemento | Dimensão / regra |
|---|---|
| Pílula | 124 × 42 px |
| Slot do símbolo | 22 × 22 px |
| Nome | `DeskAwake`, 10 px, semibold |
| Slot do nome | 58 px |
| Toggle | 32 × 18 px |
| Espaçamento horizontal entre elementos | 4 px |
| Margem lateral | 1 px |
| Borda | 1 px |
| Raio da pílula | 12 px |

A composição horizontal é:

`1 + 1 + 22 + 4 + 58 + 4 + 32 + 1 + 1 = 124 px`

O símbolo fica centralizado verticalmente no slot. Não aumentar a pílula para acomodar o spinner. Não deslocar o nome nem o toggle durante a troca de asset.

### 5.1 Componente recomendado

Usar o `Gtk.Stack` já definido em `design_e4.md`:

- `Gtk.Image` para `assets/deskawake.svg`;
- `Gtk.Image` para `assets/spinner.svg`;
- ambos com slot de 22 × 22 px;
- alternar a página visível conforme o ciclo da chamada assíncrona.

O toggle permanece visível durante todo o processamento.

## 6. Estados visuais

| Estado | Slot 22 × 22 | Toggle | Cor do símbolo |
|---|---|---|---|
| `off` | símbolo-base | habilitado, cinza | neutra da variante |
| `on` | símbolo-base | habilitado, verde | neutra da variante |
| `error` | símbolo-base | habilitado, vermelho | neutra da variante |
| chamada em voo | spinner | visível e desabilitado, preserva o último estado conhecido | neutra da variante |

### 6.1 Durante chamada em voo

- Substituir o símbolo-base pelo spinner no mesmo slot.
- Não exibir os dois simultaneamente.
- Não ocultar nem substituir o toggle.
- Desabilitar o toggle enquanto a chamada estiver pendente.
- Preservar visualmente no toggle o último estado conhecido; não antecipar o estado desejado.
- Não introduzir indicador âmbar, texto adicional, barra de progresso ou overlay.
- O ponto central não participa da rotação.

### 6.2 Entrada e saída do processamento

A troca entre símbolo-base e spinner deve ocorrer sem redimensionamento, salto de alinhamento ou mudança de cor. A duração e a curva de transição entre os dois assets podem ser refinadas na implementação da animação; não alterar a geometria aprovada para criar a transição.

## 7. Contrato de animação

A animação ainda não foi implementada. Os seguintes parâmetros foram validados na prévia animada e estão aprovados para orientar a implementação:

| Parâmetro | Decisão |
|---|---|
| Elementos móveis | as duas setas/arcos como um único conjunto |
| Elemento imóvel | ponto central |
| Centro de rotação | `(11, 11)` |
| Incremento por quadro | 15° |
| Quadros | 24 |
| Intervalo entre quadros | 40 ms |
| Duração de uma volta | 960 ms |
| Movimento | rotação contínua e linear |
| Cor | neutra, derivada do tema |
| Slot | 22 × 22 px |

A rotação deve ser aplicada ao conjunto circular das duas setas, em torno do centro geométrico. O ponto central deve ficar fora do grupo transformado — ou ser desenhado em camada posterior — para não girar, transladar ou sofrer qualquer oscilação.

O conjunto deve avançar **15° por quadro**, sem aceleração ou desaceleração durante a volta. São **24 quadros**, apresentados em intervalos de **40 ms**, totalizando **960 ms por volta**. A animação é contínua e em sentido horário. A prévia aprovada confirma o ritmo e a leitura visual pretendidos.

A animação só roda enquanto houver chamada `Toggle`/`SetActive` pendente. Ao receber resposta ou erro/timeout, interromper a animação e retornar ao símbolo-base.

A entrada e a saída do estado de processamento mantêm a transição discreta descrita na §6.2. Não aplicar desaceleração artificial ao concluir uma chamada.

**Detalhes reservados à implementação:** mecanismo de temporização GTK/GLib, estratégia de cache dos 24 quadros e tratamento de frame perdido. Esses detalhes podem variar, desde que preservem o contrato visual aprovado.


### 7.1 Prévia animada aprovada

A prévia de validação foi produzida a partir dos SVGs oficiais, com 24 quadros,
15° por quadro, 40 ms por quadro e composição do ponto central em uma camada
separada e imóvel. O resultado visual foi aprovado.

Os GIFs da prévia são artefatos de validação, não dependências de runtime.
A implementação GTK3 deve reproduzir o movimento usando os assets vetoriais e
o mecanismo de renderização escolhido para a aplicação.

## 8. Assets oficiais

Os arquivos incluídos neste pacote são a referência de implementação aprovada:

- `assets/deskawake.svg` — símbolo estático.
- `assets/spinner.svg` — duas setas curvas sólidas e ponto central.

Requisitos dos arquivos:

- SVG válido;
- `width="22"`, `height="22"` e `viewBox="0 0 22 22"`;
- uso de `currentColor`;
- nenhuma cor de estado hardcoded;
- ponto central independente dos caminhos que giram;
- sem filtros, sombras, gradientes ou dependência de fontes;
- manter a geometria aprovada.

A aplicação GTK3 deve carregar os arquivos a partir da raiz do pacote, conforme a resolução relativa a `__file__` descrita em `design_e4.md`.

## 9. Critérios de aceite visual

A implementação só deve ser considerada fiel ao design se todos os itens abaixo forem verdadeiros:

### Símbolo-base
- [ ] Renderiza em 22 × 22 px sem clipping.
- [ ] Exibe dois segmentos circulares iguais.
- [ ] Exibe dois vãos iguais em orientação diagonal oposta.
- [ ] Exibe o ponto central no centro geométrico.
- [ ] As extremidades dos arcos são arredondadas.
- [ ] O desenho permanece neutro em ON, OFF e ERROR.

### Spinner
- [ ] Exibe duas setas curvas com preenchimento sólido.
- [ ] As pontas não são desenhadas como linhas ou contornos.
- [ ] Cada ponta está integrada ao eixo do arco correspondente.
- [ ] As duas setas são simétricas e opostas por 180°.
- [ ] Os vãos diagonais continuam visualmente perceptíveis.
- [ ] O ponto central permanece imóvel.
- [ ] As setas giram como um único conjunto, sem dessincronização.

### Widget e estados
- [ ] A troca de símbolo para spinner não altera a geometria da pílula.
- [ ] O spinner ocupa exatamente o slot de 22 × 22 px.
- [ ] O toggle continua visível e desabilitado durante chamada pendente.
- [ ] O toggle preserva o último estado conhecido durante a chamada.
- [ ] Somente o toggle usa as cores de estado.
- [ ] As variantes clara e escura alteram apenas as cores neutras conforme a paleta definida.

## 10. Não fazer

- Não colorir o símbolo de verde quando ON.
- Não colorir o spinner de âmbar durante processamento.
- Não mover, girar ou animar o ponto central.
- Não substituir as setas sólidas por setas de contorno.
- Não usar uma seta maior que a outra.
- Não alterar a inclinação diagonal dos vãos para uma posição vertical simétrica.
- Não fechar os vãos.
- Não transformar o símbolo em um círculo completo.
- Não alterar o tamanho da pílula ou do slot para acomodar o spinner.
- Não adicionar texto de “carregando”, barra, halo ou efeito de pulsação.
- Não introduzir animação quando não houver chamada pendente.
- Não modificar a lógica do daemon ou o contrato D-Bus para implementar a apresentação visual.

## 11. Relação com `design_e4.md`

Este documento fixa a forma visual que foi aprovada após a elaboração de `design_e4.md`. As regras de arquitetura, integração GTK, D-Bus, persistência, tema, compositor, janela, menu, arrasto e testes continuam sob responsabilidade do documento E4 e da `spec.md`.

Em particular, permanecem válidas as definições E4 de:

- janela GTK3 de 124 × 42 px;
- símbolo/spinner em `Gtk.Stack` de 22 × 22 px;
- `currentColor` resolvido para a variante clara/escura;
- pré-renderização de 24 quadros com rotação de 15° e intervalo de 40 ms (960 ms por volta);
- troca de símbolo pelo spinner durante chamadas assíncronas;
- toggle visível e insensível durante a chamada;
- estado público limitado a `on`, `off` e `error`;
- ausência de novas dependências de runtime.

Este documento não autoriza mudanças em `core/`, no daemon, nos inibidores, na CLI, no contrato D-Bus, na configuração ou na entrega E5.

---

## 12. Pacote entregue

```text
design_visual_aprovado.md
assets/
├── deskawake.svg
└── spinner.svg
preview/
├── deskawake_spinner_960ms.gif
└── deskawake_spinner_preview_large.gif
```

**Status final:** identidade visual e animação aprovadas em prévia. Próxima etapa: implementar no GTK3 conforme o contrato da §7, sem reabrir as decisões geométricas ou os parâmetros de movimento já aprovados.
