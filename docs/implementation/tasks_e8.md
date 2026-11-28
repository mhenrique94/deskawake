# Tasks: E8 — Empacotamento e Distribuição (`.deb` + GitHub Releases)

**Feature:** DeskAwake — E8 | **Data:** 2026-11-22 | **Estimativa:** ≈ 9 h (36 tasks)
**Referências:** [`spec.md`](spec.md) (decisões 34–38, “Meta” e “Verificação”), [`design_e8.md`](design_e8.md) (decisões 1–26, §3–§10), [`DELIVERY_MAP.md`](DELIVERY_MAP.md) §E8 e G-E8, [`design_e7.md`](design_e7.md) (layout per-user e instalador).

> **Nome do arquivo:** este projeto versiona os artefatos do pipeline como `tasks_eN.md` em
> `docs/implementation/` (mesma convenção de `design_eN.md` e das entregas E1–E5). O `tasks.md`
> genérico do processo corresponde a este `tasks_e8.md`.

## Resumo

- Total de tasks: **37**
- Estimativa total: **≈ 9 h** (~1,5 dias de trabalho focado, incluindo build, container e checklists manuais)
- Dependências externas:
  - branch `feat/e8-distribuicao` já criada a partir da `main` **após o merge da E7** (merge `f94964a`);
  - `dpkg-deb` 1.23.7 (validado nesta máquina), `docker` com acesso funcional, `gh` autenticado como `mhenrique94`;
  - rede no container `ubuntu:24.04` para `apt-get update/install`;
  - máquinas físicas Mint 22.3 MATE/X11 e Kubuntu 26.04/Plasma 6.6 para as checklists manuais;
  - tag `v0.1.0` criada **depois** do merge e da validação com `workflow_dispatch`;
  - **nenhuma** migration, serviço novo, segredo ou dependência de runtime.
- Baseline atual (branch limpa): `.venv/bin/python -m pytest tests/unit -q` ⇒ **326 passed**;
  `.venv/bin/python -m pytest -q` ⇒ **398 passed, 1 skipped**.
- Gate: **G-E8** — `pytest` completo verde (inclui `test_packaging.py` e a versão do changelog);
  `bash -n` limpo em `install.sh`, `uninstall.sh`, `verify.sh`, `packaging/build-deb.sh` e
  `packaging/test-deb.sh`; `packaging/build-deb.sh` gera `.deb`/tarball/`SHA256SUMS` com
  `sha256sum -c` OK; `dpkg-deb -I/-c` contém o layout do §3 e não contém `__pycache__`/`docs/`/`tests/`;
  `packaging/test-deb.sh` instala, valida `status` = 3, remove e não deixa resíduos em `ubuntu:24.04`;
  `install.sh` recusa com o pacote presente; `uninstall.sh` avisa; `verify.sh` encontra a instalação
  system-wide; READMEs pt-BR/inglês cobrem `.deb`, checksums, atualização, remoção e coexistência;
  `workflow_dispatch` verde e tag `v0.1.0` publica os três anexos.
- Fora de escopo (não criar nesta entrega): AUR, Flatpak, AppImage, Snap, repositório APT/PPA,
  assinatura GPG, auto-update, split `deskawake-gtk`/`deskawake-plasma`, manpage, `postinst`/`prerm`/
  `postrm`, serviço `systemd` de sistema e qualquer mudança em `core/`, `ui_gtk/`, `plasmoid/`,
  `bin/` ou `data/`.
- Referência de comportamento: em conflito, `spec.md` vence o `design_e8.md`; o `DELIVERY_MAP.md`
  §E8 resume as decisões executáveis e o G-E8 é o critério de saída.

**Sequência:** setup → metadados (TDD) → build (TDD) → container (TDD) → coexistência (TDD) → CI
(TDD) → READMEs (TDD) → emenda da spec → gate/auditoria → PR de código → checklists manuais →
merge → `workflow_dispatch` → PR de docs → tag/release → limpeza dos docs transitórios.

**Regras de teste que valem para todas as tasks:**

- `tests/unit/test_packaging.py` é **estático e headless**: lê arquivos como texto/JSON, usa
  `bash -n` e `subprocess` apenas para validar sintaxe; **não** executa `dpkg-deb`, `docker`, `apt`,
  `gh` nem o build durante a suíte unitária.
- O container e o build real são validados por comandos explícitos nas tasks de artefato (T-10,
  T-13) e no gate (T-28), nunca dentro do pytest unitário.
- TDD: cada task de teste vem antes da implementação e o RED esperado deve ser confirmado (arquivo
  ausente ou teste falhando). Se um teste passar antes da implementação, é regressão: registrar e
  não “implementar” o que já existe.
- Comandos executados nesta máquina: `.venv/bin/python -m pytest` (pytest 9.2.0). Em CI, o workflow
  usa `python3 -m pytest` depois de instalar o pytest; não criar `.venv` no CI.
- Os testes existentes de E1–E7 **não podem ser enfraquecidos**. A única mudança de expectativa
  permitida é a mensagem de “não instalado” do `verify.sh` (T-14), porque o contrato passa a citar
  as duas opções de instalação.
- **`sudo` é proibido dentro de `install.sh`, `uninstall.sh` e `verify.sh`** (testes
  `test_*_script_has_no_privilege_escalation` já existentes). As mensagens e o README podem citar
  `sudo apt install/remove`; os scripts não podem executar nem imprimir a palavra `sudo`.
- Nenhum arquivo de `packaging/`, workflow, script ou teste novo cita `docs/`, `design_e8.md`,
  `tasks_e8.md`, `spec.md`, `DELIVERY_MAP.md`, `AC-*` ou `T-*` em código/comentários. Os READMEs
  mantêm o link para `docs/implementation/spec.md` exigido pelo teste da E7.
- `docs/implementation/` (incluindo este arquivo) é transitório: fica fora do PR de código e nunca
  é citado em commits/PRs de entrega.

## Priorização

Score = (Impacto × Confiança) / Esforço (H=3, M=2, L=1).

| Grupo | Impacto | Confiança | Esforço | Score | Execução |
|---|---|---|---|---|---|
| Fundação e metadados do pacote (T-01–T-07) | 3 | 3 | 2 | 4,5 | Primeiro — destrava build e testes |
| Build e artefatos (T-08–T-10) | 3 | 2 | 3 | 2,0 | Neste ciclo — é o núcleo da entrega |
| Container e coexistência (T-11–T-18) | 3 | 3 | 2 | 4,5 | Assim que o build existir |
| CI e release (T-19–T-21, T-34, T-36) | 3 | 2 | 2 | 3,0 | Neste ciclo, antes da tag |
| READMEs e emenda da spec (T-22–T-26) | 2 | 3 | 2 | 3,0 | Fecha a documentação do canal |
| Gate, auditoria, PR e checklists (T-27–T-33, T-35) | 3 | 2 | 2 | 3,0 | Fecha o G-E8 |

Nenhuma task cai em backlog (< 2): a E8 é uma entrega única e o gate só fecha com todas as tasks
automáticas; as checklists manuais são registradas no PR.

## Rodadas de execução

Cortes de contexto aprovados em 2026-11-22. Cada rodada é uma sessão independente e para no
critério de saída indicado; a rodada seguinte começa com a árvore limpa e os commits parciais já
feitos. As tags `[R1]`–`[R4]` em cada task marcam o corte.

| Rodada | Tasks | Critério de saída |
|---|---|---|
| **R1 — Fundação + build** | T-01–T-10 | `dist/` com `.deb`, tarball e `SHA256SUMS`; testes de metadados/build verdes |
| **R2 — Instalação real + coexistência** | T-11–T-18 | `packaging/test-deb.sh` verde em `ubuntu:24.04`; `install.sh` recusando; scripts adaptados |
| **R3 — CI + docs + gate** | T-19–T-28 + T-32 | Workflow validado, READMEs, emenda da spec, G-E8 verde e PR de código aberto |
| **R4 — Validação manual + release + limpeza** | T-29–T-31 + T-33–T-37 | Checklists preenchidas, merge, `workflow_dispatch`, tag `v0.1.0`, release conferido e docs transitórios restantes removidos (`DELIVERY_MAP.md` e `visual/`) |

Os cortes são de **execução**, não de escopo: todas as tasks continuam obrigatórias para fechar o
G-E8. Na R3 o PR de código é aberto com as checklists manuais ainda pendentes; a R4 as preenche
antes do merge. A R4 depende de aprovação explícita para merge/tag/release e das máquinas
Mint/Kubuntu.

## Tasks

### 0. Setup e fundação

- [ ] **T-01** [R1]: Confirmar branch, baseline e ferramentas
  - Comandos:
    - `git branch --show-current` ⇒ `feat/e8-distribuicao`
    - `git merge-base --is-ancestor f94964a HEAD` ⇒ exit 0 (E7 mergeada)
    - `git status --short` ⇒ vazio (antes de criar este `tasks_e8.md`)
    - `.venv/bin/python -m pytest tests/unit -q` ⇒ **326 passed**
    - `.venv/bin/python -m pytest -q` ⇒ **398 passed, 1 skipped**
    - `command -v dpkg-deb docker gh gzip sha256sum` ⇒ todos com caminho absoluto
    - `dpkg-deb --help | grep -q -- --root-owner-group` ⇒ exit 0
    - `docker info >/dev/null` ⇒ exit 0
    - `gh auth status` ⇒ conta `mhenrique94` ativa
  - Critério: branch correta, E7 no histórico, baseline verde e ferramentas disponíveis. Se o
    baseline falhar, parar e resolver antes da E8; não recriar a branch nem rebasear a partir da
    `main` sem confirmação.
  - Estimativa: 5min

- [ ] **T-02** [R1]: Escrever os testes RED dos metadados do pacote
  - Arquivo: `tests/unit/test_packaging.py` (novo)
  - Estrutura: `REPO_ROOT = Path(__file__).resolve().parents[2]`, `PACKAGING = REPO_ROOT / "packaging"`,
    `DEBIAN = PACKAGING / "debian"`; helpers `_text(path)` e `_read(path)`.
  - Testes (nomes canônicos do design §10.1, mais dois contratos de decisão):
    - `test_control_template_contract` — `Package: deskawake`, `Architecture: all`,
      `Maintainer: Marcelo Silva <contato@manivasoftware.com.br>`, `Depends:` com
      `python3 (>= 3.10)`, `python3-gi`, `python3-dbus`, `gir1.2-gtk-3.0`, `systemd`,
      `libglib2.0-bin`; `Suggests: fonts-inter`; **sem** `Recommends:`; `Section: utils`,
      `Priority: optional`, `Homepage: https://github.com/mhenrique94/deskawake`,
      `Version: @VERSION@` e `Installed-Size: @INSTALLED_SIZE@`.
    - `test_changelog_top_version` — primeira linha começa com
      `deskawake ({core.__version__}) unstable;` e o trailer contém
      `-- Marcelo Silva <contato@manivasoftware.com.br>`.
    - `test_copyright_contract` — `Format:` DEP-5, `Files: *`, a linha legal da E6/E7, `License: MIT`
      e o corpo MIT idêntico ao trecho correspondente do `LICENSE` (comparar o bloco de permissão e
      o aviso `THE SOFTWARE IS PROVIDED "AS IS"`).
    - `test_no_maintainer_scripts` — `packaging/debian/postinst`, `prerm` e `postrm` **não** existem;
      o `build-deb.sh` não cria `DEBIAN/postinst`, `DEBIAN/prerm` nem `DEBIAN/postrm`.
    - `test_gitignore_excludes_dist` — `.gitignore` contém a linha `dist/`.
    - `test_packaging_has_no_spec_paths` — `packaging/` existe e nenhum arquivo contém `docs/`,
      `design_e`, `tasks_e`, `spec.md`, `DELIVERY_MAP`, `AC-` ou `T-` seguido de dígitos (o
      diretório ausente falha o teste, garantindo o RED).
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "control or changelog or copyright or maintainer or gitignore or no_spec_paths"`
  - Critério: falha (RED) — `FileNotFoundError` para `packaging/debian/control.in` (ou para o
    changelog/`.gitignore` de `dist/`, conforme a ordem de coleta) e `AssertionError` em
    `test_packaging_has_no_spec_paths` porque `packaging/` ainda não existe.
  - Estimativa: 20min

- [ ] **T-03** [R1]: Criar `packaging/debian/control.in`
  - Arquivo: `packaging/debian/control.in`
  - Contrato: design §4, bloco integral — `Package`, `Version: @VERSION@`, `Architecture: all`,
    `Maintainer`, `Installed-Size: @INSTALLED_SIZE@`, `Depends` com as seis dependências na ordem
    aprovada, `Suggests: fonts-inter`, `Section: utils`, `Priority: optional`, `Homepage`, `Bugs` e
    `Description` longa em pt-BR (linhas de continuação com um espaço e o parágrafo separado por
    ` .`).
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "control"`
  - Critério: teste verde (GREEN); nenhum `Recommends:`; placeholders preservados para o build.
  - Estimativa: 10min

- [ ] **T-04** [R1]: Estender `tests/unit/test_version.py` com a versão do changelog
  - Arquivo: `tests/unit/test_version.py` (append)
  - Conteúdo:
    - helper `_changelog_version()` que lê `packaging/debian/changelog` e casa
      `^deskawake \((\d+\.\d+\.\d+)\) ` na primeira linha;
    - `test_version_matches_changelog()` comparando com `core.__version__`.
  - Comando: `.venv/bin/python -m pytest tests/unit/test_version.py -q`
  - Critério: falha (RED) — `FileNotFoundError` para `packaging/debian/changelog`; os três testes
    anteriores de versão continuam verdes.
  - Estimativa: 5min

- [ ] **T-05** [R1]: Criar `packaging/debian/changelog`
  - Arquivo: `packaging/debian/changelog`
  - Conteúdo mínimo:
    ```
    deskawake (0.1.0) unstable; urgency=medium

      * Versão inicial com daemon D-Bus, widget GTK3 e Plasmoid.

     -- Marcelo Silva <contato@manivasoftware.com.br>  Sun, 22 Nov 2026 00:00:00 -0300
    ```
  - Comandos:
    - `.venv/bin/python -m pytest tests/unit/test_version.py -q` ⇒ verde
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "changelog"` ⇒ verde
  - Critério: topo igual a `core.__version__` e trailer com o maintainer aprovado; o changelog não
    pode ter linha em branco inicial.
  - Estimativa: 10min

- [ ] **T-06** [R1]: Criar `packaging/debian/copyright` em DEP-5
  - Arquivo: `packaging/debian/copyright`
  - Conteúdo: `Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/`,
    `Upstream-Name: deskawake`, `Source: https://github.com/mhenrique94/deskawake`,
    `Files: *`, `Copyright: 2026 Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79`,
    `License: MIT` e o texto MIT completo idêntico ao `LICENSE` (sem o símbolo © na linha legal
    do pacote). Sem seções por arquivo.
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "copyright"`
  - Critério: teste verde (GREEN); o texto MIT coincide com o `LICENSE`; a linha legal não tem ©.
  - Estimativa: 15min

- [ ] **T-07** [R1]: Ignorar `dist/` no git
  - Arquivo: `.gitignore`
  - Conteúdo: acrescentar `dist/` (uma linha, no fim do bloco de artefatos).
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "gitignore"`
  - Critério: teste verde (GREEN); `git check-ignore -v dist/teste` ⇒ regra `dist/`.
  - Estimativa: 5min

### 1. Build do `.deb` (TDD)

- [ ] **T-08** [R1]: Escrever os testes RED do build
  - Arquivo: `tests/unit/test_packaging.py` (append)
  - Testes:
    - `test_build_script_syntax` — `bash -n packaging/build-deb.sh` ⇒ returncode 0.
    - `test_build_script_contract` — exige `dpkg-deb --build`, `--root-owner-group`, `-Zxz`,
      `SOURCE_DATE_EPOCH`, `git archive`, `gzip -9n`, `sha256sum`, remoção de `__pycache__`,
      render de `@EXEC@`, validação de `pyproject.toml`, `plasmoid/metadata.json` e
      `packaging/debian/changelog`; **proíbe** `sudo`, `debhelper` e `fpm`.
    - `test_build_artifacts_names` — o script contém `deskawake_${VERSION}_all.deb`,
      `deskawake-${VERSION}.tar.gz` e `SHA256SUMS`.
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "build_script or build_artifacts"`
  - Critério: falha (RED) — `FileNotFoundError` para `packaging/build-deb.sh` em
    `test_build_script_syntax`.
  - Estimativa: 20min

- [ ] **T-09** [R1]: Implementar `packaging/build-deb.sh`
  - Arquivo: `packaging/build-deb.sh` (novo, `chmod 755`)
  - Contrato: design §5.1, itens 1–14 —
    - resolver `REPO_ROOT` a partir de `BASH_SOURCE` e `cd` para ele;
    - flags `--output DIR` (padrão `dist/`) e `--allow-dirty`; flag desconhecida ⇒ exit 2; sem
      `--version`;
    - exigir `dpkg-deb`, `git`, `gzip` e `sha256sum` (e `python3` para ler a versão);
    - ler `core.__version__` com `python3 -c 'import core; print(core.__version__)'`, validar semver
      `^[0-9]+\.[0-9]+\.[0-9]+$` e comparar com `pyproject.toml`, `plasmoid/metadata.json` e topo
      do `packaging/debian/changelog`; divergência ⇒ exit 1 com mensagem clara;
    - recusar árvore suja (`git status --porcelain`) salvo `--allow-dirty`;
    - staging em `mktemp -d`; copiar `core/`, `ui_gtk/`, `assets/`, `bin/deskawake` e `plasmoid/`
      para os caminhos do §3; remover `__pycache__`, `*.pyc`, `*.pyo`, `*.pyd`; diretórios `0755`,
      arquivos `0644`, `bin/deskawake` `0755`;
    - symlink relativo `usr/bin/deskawake -> ../lib/deskawake/bin/deskawake`;
    - renderizar os três templates de `data/` com `sed` e `@EXEC@ = /usr/bin/deskawake`; falhar se
      `@EXEC@` sobrar;
    - copiar `copyright` e gerar `changelog.Debian.gz` com `gzip -9n`;
    - gerar `DEBIAN/control` a partir de `control.in`, substituindo `@VERSION@` e
      `@INSTALLED_SIZE@` (`du -sk --exclude=DEBIAN`); falhar se sobrar placeholder;
    - gerar `DEBIAN/md5sums` com arquivos regulares, caminhos relativos e ordem determinística;
    - normalizar mtimes para `SOURCE_DATE_EPOCH` (padrão `git log -1 --format=%ct`, aceitar a
      variável do ambiente);
    - `dpkg-deb --build --root-owner-group -Zxz "$stage" "dist/deskawake_${VERSION}_all.deb"`;
    - tarball `git archive HEAD --prefix="deskawake-${VERSION}/" | gzip -9n > dist/...`; em
      `--allow-dirty`, avisar que o tarball é do `HEAD`;
    - `SHA256SUMS` com nomes relativos e validação `(cd dist && sha256sum -c SHA256SUMS)`;
    - smoke checks no artefato (`dpkg-deb --info`, `--contents` sem `__pycache__`/`docs/`/`tests/`,
      symlink presente, `--field` versão/arquitetura) e impressão dos caminhos/tamanhos.
  - Comandos:
    - `bash -n packaging/build-deb.sh` ⇒ exit 0
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "build_script or build_artifacts"` ⇒ GREEN
  - Critério: script idempotente (recria staging e sobrescreve artefatos), sem `sudo`, sem
    `debhelper`/`fpm`, com os tokens exigidos; modo `755`.
  - Estimativa: 40min

- [ ] **T-10** [R1]: Construir o pacote localmente e inspecionar os artefatos
  - Comandos (o `--allow-dirty` é necessário enquanto este `tasks_e8.md` estiver não versionado;
    com o código já commitado, o tarball do `HEAD` corresponde ao `.deb`):
    - `packaging/build-deb.sh --allow-dirty` ⇒ exit 0; imprime os três caminhos em `dist/`
    - `ls -l dist/deskawake_0.1.0_all.deb dist/deskawake-0.1.0.tar.gz dist/SHA256SUMS`
    - `(cd dist && sha256sum -c SHA256SUMS)` ⇒ dois `OK`
    - `dpkg-deb -I dist/deskawake_0.1.0_all.deb` ⇒ `Package: deskawake`, `Version: 0.1.0`,
      `Architecture: all`, maintainer, `Depends`, `Suggests: fonts-inter`, sem `Recommends`
    - `dpkg-deb -f dist/deskawake_0.1.0_all.deb Section Priority Installed-Size` ⇒ `utils`,
      `optional`, inteiro > 0
    - `dpkg-deb -c dist/deskawake_0.1.0_all.deb | grep -E '__pycache__|docs/|tests/'` ⇒ sem saída
    - `dpkg-deb -c dist/deskawake_0.1.0_all.deb | grep -q 'usr/bin/deskawake -> ../lib/deskawake/bin/deskawake'`
    - conferir no `--contents` os caminhos do §3: `usr/lib/deskawake/{bin,core,ui_gtk,assets}`,
      `usr/share/dbus-1/services/org.local.DeskAwake.service`,
      `etc/xdg/autostart/deskawake-daemon.desktop`, `.../deskawake-widget.desktop`,
      `usr/share/plasma/plasmoids/org.local.deskawake/{metadata.json,preview.png,contents/ui/main.qml,contents/ui/assets/*.svg}`,
      `usr/share/doc/deskawake/{copyright,changelog.Debian.gz}`
    - `tar -tzf dist/deskawake-0.1.0.tar.gz | head` ⇒ prefixo `deskawake-0.1.0/`; contém o repo,
      não contém `dist/`
  - Critério: os três artefatos existem, checksums validam e o layout bate com o §3; nenhum
    `__pycache__`, `docs/`, `tests/`, `data/`, `install.sh`, `pyproject.toml` ou `uv.lock` dentro
    do `.deb`.
  - Estimativa: 15min

### 2. Smoke test em container (TDD)

- [ ] **T-11** [R2]: Escrever o teste RED do `packaging/test-deb.sh`
  - Arquivo: `tests/unit/test_packaging.py` (append)
  - Teste `test_test_deb_contract`:
    - `bash -n packaging/test-deb.sh` ⇒ 0;
    - contém `ubuntu:24.04`, `/pkg`, `apt-get install`, `--no-install-recommends`, `procps`,
      `deskawake status`, `apt-get remove`, `__pycache__`, `docs/`, `tests/` e detecção de
      `docker`/`podman`.
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "test_deb"`
  - Critério: falha (RED) — `FileNotFoundError` para `packaging/test-deb.sh`.
  - Estimativa: 15min

- [ ] **T-12** [R2]: Implementar `packaging/test-deb.sh`
  - Arquivo: `packaging/test-deb.sh` (novo, `chmod 755`)
  - Contrato: design §5.2 —
    - resolver `REPO_ROOT` e a versão (`core.__version__`);
    - detectar `docker` ou `podman`; se ausente, exit 2 com mensagem clara;
    - montar `dist/` como somente leitura em `/pkg` e rodar `ubuntu:24.04` com
      `bash -c 'set -euo pipefail; ...'`;
    - no container: `apt-get update`; `apt-get install -y --no-install-recommends
      /pkg/deskawake_${VERSION}_all.deb procps`;
    - validar `dpkg-query -W -f='${Status}' deskawake` contendo `install ok installed`;
      `/usr/bin/deskawake` é symlink para `/usr/lib/deskawake/bin/deskawake`;
      `.service`, os dois autostarts e o Plasmoid nos caminhos do §3;
      `grep -q '^Exec=/usr/bin/deskawake daemon$'` no `.service` e no autostart do daemon;
      `grep -q '^Exec=/usr/bin/deskawake ui$'` no autostart do widget;
      `deskawake --help` sai 0;
      sem sessão D-Bus, `deskawake status` imprime `off` e sai **3**;
      nenhum processo `deskawake daemon` iniciado pelo install (usar `pgrep -f '[d]eskawake daemon'`);
      `dpkg-deb --contents` não lista `__pycache__`, `*.pyc`, `docs/` nem `tests/`;
    - remover com `apt-get remove -y deskawake`; validar que `/usr/lib/deskawake`,
      `/usr/bin/deskawake`, `.service`, autostarts e Plasmoid sumiram e que `dpkg-query` já não
      reporta o pacote;
    - repetir instalação/remoção uma vez (idempotência do `apt`).
  - Comandos:
    - `bash -n packaging/test-deb.sh` ⇒ 0
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "test_deb"` ⇒ GREEN
  - Critério: script sem `sudo`, com exit 2 quando não há engine, e modo `755`.
  - Estimativa: 30min

- [ ] **T-13** [R2]: Rodar o smoke test e validar a recusa do `install.sh` no container
  - Pré-condição: T-10 concluída (`dist/deskawake_0.1.0_all.deb` existe) e Docker funcional.
  - Comandos:
    - `packaging/test-deb.sh` ⇒ exit 0; log com install, `status` = `off`/3, remoção e nova
      instalação/remoção sem resíduo; nenhum `deskawake daemon` iniciado
    - Checagem comportamental do gate 6 (pacote presente ⇒ `install.sh` recusa), em container
      descartável com o repo montado somente leitura:
      ```bash
      docker run --rm \
        -v "$PWD/dist:/pkg:ro" -v "$PWD:/src:ro" \
        ubuntu:24.04 bash -c '
          set -euo pipefail
          export DEBIAN_FRONTEND=noninteractive
          apt-get update >/dev/null
          apt-get install -y --no-install-recommends /pkg/deskawake_0.1.0_all.deb >/dev/null
          set +e
          out=$(HOME=/root /src/install.sh --only-mate 2>&1)
          rc=$?
          set -e
          test "$rc" -eq 1
          printf "%s\n" "$out" | grep -q "apt remove deskawake"
        '
      ```
  - Critério: smoke verde; `install.sh` sai 1 com a mensagem aprovada (sem a palavra `sudo`);
    `apt-get remove` remove todos os caminhos do pacote e o `dpkg-query` deixa de reportar.
  - Estimativa: 20min

### 3. Coexistência com a instalação per-user (TDD)

- [ ] **T-14** [R2]: Escrever os testes RED de coexistência e ajustar a expectativa do `verify.sh`
  - Arquivo: `tests/unit/test_packaging.py` (append) e `tests/unit/test_scripts.py` (ajuste pontual)
  - Testes novos:
    - `test_install_script_refuses_system_package` — `install.sh` contém
      `system_package_installed`, `dpkg-query -W -f='${Status}'`, `install ok installed`,
      `/usr/lib/deskawake`, `apt remove deskawake`; a checagem é chamada **antes** da detecção por
      `XDG_CURRENT_DESKTOP`; não contém `sudo`.
    - `test_uninstall_script_warns_system_package` — `uninstall.sh` contém a mesma detecção e um
      `warn` citando que o pacote system-wide não é removido por ele; não contém remoção de
      `/usr/*` (`rm -rf -- /usr`, `rm -rf /usr`) nem `apt-get`.
    - `test_verify_script_system_fallback` — `verify.sh` contém `/usr/bin/deskawake` e
      `/usr/share/dbus-1/services/org.local.DeskAwake.service` no fallback; a mensagem de “não
      instalado” cita `./install.sh` **e** o `.deb` do release.
  - Ajuste existente: em `tests/unit/test_scripts.py`, `test_verify_script_preconditions` deixa de
    exigir a mensagem antiga `"DeskAwake não instalado; rode ./install.sh"` e passa a aceitar a
    mensagem com as duas opções (manter a asserção de `dependência de diagnóstico ausente:` e
    `trap`).
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py tests/unit/test_scripts.py -v -k "refuses or warns or fallback or preconditions"`
  - Critério: falha (RED) nos três testes novos e no de preconditions atualizado (mensagem ainda
    não existe); os demais testes de scripts continuam verdes.
  - Estimativa: 20min

- [ ] **T-15** [R2]: Adaptar `install.sh` para recusar com o pacote presente
  - Arquivo: `install.sh`
  - Contrato: design §7 —
    - função `system_package_installed()` com
      `dpkg-query -W -f='${Status}' deskawake 2>/dev/null | grep -q 'install ok installed'`
      **ou** `[[ -e /usr/lib/deskawake ]]`;
    - chamada logo após a validação de `HOME`/`XDG_DATA_HOME` e **antes** da detecção de desktop;
    - mensagem de recusa com `apt remove deskawake` (sem `sudo`) e a alternativa
      `use /usr/bin/deskawake`; exit 1;
    - `--install-deps` continua funcionando para diagnóstico, mas não instala o perfil quando o
      pacote está presente;
    - nenhuma escrita em `$HOME` antes da recusa.
  - Comandos:
    - `bash -n install.sh` ⇒ 0
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "install_script_refuses"` ⇒ GREEN
    - `.venv/bin/python -m pytest tests/unit/test_scripts.py -v -k "install"` ⇒ sem regressão
  - Critério: teste verde; `grep -n 'sudo' install.sh` ⇒ sem saída; a ordem da checagem é anterior a
    `XDG_CURRENT_DESKTOP` no fluxo principal.
  - Estimativa: 15min

- [ ] **T-16** [R2]: Adaptar `uninstall.sh` para apenas avisar
  - Arquivo: `uninstall.sh`
  - Contrato: design §7 — mesma detecção (`dpkg-query` **ou** `/usr/lib/deskawake`), usada apenas
    para `warn` “o pacote system-wide não é removido por este script; use o gerenciador de pacotes
    (`apt remove deskawake`)”; nunca remove `/usr/*`, nunca chama `apt`; a remoção per-user e o
    `--purge` continuam iguais.
  - Comandos:
    - `bash -n uninstall.sh` ⇒ 0
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "uninstall_script_warns"` ⇒ GREEN
    - `.venv/bin/python -m pytest tests/unit/test_scripts.py -v -k "uninstall"` ⇒ sem regressão
  - Critério: teste verde; `grep -E 'rm -rf .*/usr|apt-get' uninstall.sh` ⇒ sem saída; sem `sudo`.
  - Estimativa: 10min

- [ ] **T-17** [R2]: Adaptar `verify.sh` para o fallback system-wide
  - Arquivo: `verify.sh`
  - Contrato: design §7 —
    - resolver o binário na ordem `~/.local/bin/deskawake` → `~/.local/share/deskawake/bin/deskawake`
      → `/usr/bin/deskawake`;
    - resolver o `.service` em `${XDG_DATA_HOME:-~/.local/share}/dbus-1/services` →
      `/usr/share/dbus-1/services/org.local.DeskAwake.service`;
    - mensagem de “não instalado” citando `./install.sh` e o `.deb` do release;
    - avisar (sem falhar) se as duas instalações existirem;
    - o restante do script (estado, `systemd-inhibit`, backend MATE/KDE) não muda.
  - Comandos:
    - `bash -n verify.sh` ⇒ 0
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "verify_script_system_fallback"` ⇒ GREEN
    - `.venv/bin/python -m pytest tests/unit/test_scripts.py -v -k "verify"` ⇒ sem regressão
  - Critério: teste verde; `grep -n 'sudo' verify.sh` ⇒ sem saída; nenhuma chamada a `apt`.
  - Estimativa: 15min

- [ ] **T-18** [R2]: Rodar os testes de scripts e a sintaxe
  - Comandos:
    - `for f in install.sh uninstall.sh verify.sh; do bash -n "$f"; done` ⇒ exit 0
    - `.venv/bin/python -m pytest tests/unit/test_scripts.py tests/unit/test_packaging.py -v` ⇒ verde
    - `.venv/bin/python -m pytest tests/unit -q` ⇒ 0 failures (baseline 326 + novos testes)
  - Critério: nenhuma regressão E1–E7; os únicos testes alterados são os de mensagem do `verify.sh`
    (T-14) e os novos de coexistência.
  - Estimativa: 5min

### 4. CI e release (TDD)

- [ ] **T-19** [R3]: Escrever o teste RED do workflow
  - Arquivo: `tests/unit/test_packaging.py` (append)
  - Teste `test_workflow_contract` lendo `.github/workflows/release.yml`:
    - `tags: ["v*"]` (ou `- "v*"`), `workflow_dispatch`, `permissions:` com `contents: write`,
      `ubuntu-latest`, `fetch-depth: 0`;
    - `packaging/build-deb.sh`, `packaging/test-deb.sh`, `sha256sum -c SHA256SUMS`,
      `gh release`, `upload-artifact`, `SHA256SUMS`, `RUNNER_TEMP` e `--notes-file`;
    - validação da tag com `GITHUB_REF_NAME` e `v$VERSION`;
    - anexos explícitos `dist/deskawake_${VERSION}_all.deb`, `dist/deskawake-${VERSION}.tar.gz`,
      `dist/SHA256SUMS`;
    - **proíbe** `gpg`.
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "workflow"`
  - Critério: falha (RED) — `FileNotFoundError` para `.github/workflows/release.yml`.
  - Estimativa: 15min

- [ ] **T-20** [R3]: Criar `.github/workflows/release.yml`
  - Arquivo: `.github/workflows/release.yml`
  - Contrato: design §9, YAML integral —
    - trigger `push` em tags `v*` + `workflow_dispatch`;
    - `permissions: contents: write`;
    - job `build` em `ubuntu-latest` com `actions/checkout@v4`/`fetch-depth: 0`;
    - passos: validar tag × `core.__version__`; build; smoke test; checksums; gerar notas em
      `$RUNNER_TEMP/release-notes.md`; `gh release create/upload` com os três caminhos explícitos;
      `actions/upload-artifact@v4` apenas em `workflow_dispatch`.
  - Comandos:
    - `.venv/bin/python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/release.yml').read_text())"` ⇒ exit 0 (PyYAML 6.0.3 no `.venv`)
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "workflow"` ⇒ GREEN
  - Critério: YAML válido, `contents: write` só no job (ou topo), nenhum segredo além de
    `${{ github.token }}`, sem GPG/APT repo/auto-update.
  - Estimativa: 20min

- [ ] **T-21** [R3]: Validar o workflow estaticamente
  - Comandos:
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "workflow"` ⇒ verde
    - `grep -nE "gpg|debhelper|fpm|sudo" .github/workflows/release.yml` ⇒ sem saída
    - `grep -n "RUNNER_TEMP" .github/workflows/release.yml` ⇒ presente; nenhum
      `dist/release-notes.md`
  - Critério: o workflow não publica as notas como anexo; os três anexos são exatamente os do
    design; `workflow_dispatch` não publica release.
  - Estimativa: 10min

### 5. READMEs (TDD)

- [ ] **T-22** [R3]: Escrever o teste RED da documentação do `.deb`
  - Arquivo: `tests/unit/test_packaging.py` (append)
  - Teste `test_readmes_document_deb` (parametrizado em `README.md`/`README.en.md`):
    - ambos: `.deb`, `deskawake_0.1.0_all.deb`, `deskawake-0.1.0.tar.gz`, `SHA256SUMS`,
      `sha256sum -c`, `apt install`, `apt remove`, atualização manual e coexistência;
    - pt-BR: “atualiz”, “coexist”, “remov” e aviso para rodar `./uninstall.sh` antes de instalar o
      `.deb`;
    - inglês: “update”, “coexist”, “remove” e “run `./uninstall.sh` before installing the `.deb`”.
  - Comando: `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "readmes_document_deb"`
  - Critério: falha (RED) — os READMEs ainda não têm `SHA256SUMS` nem o fluxo `.deb`.
  - Estimativa: 10min

- [ ] **T-23** [R3]: Atualizar `README.md` (pt-BR)
  - Arquivo: `README.md`
  - Conteúdo:
    - subseção “Instalação via `.deb` (system-wide)” logo após a instalação per-user:
      `sudo apt install ./deskawake_0.1.0_all.deb` (recomendado; `dpkg -i` só como fallback),
      `sudo apt remove deskawake`, preservação de `~/.config/deskawake` e
      `~/.local/state/deskawake`;
    - “Atualização” com download do próximo `.deb` + `sudo apt install ./...`; sem auto-update;
    - “Integridade” com `sha256sum -c SHA256SUMS` e aviso de que não há GPG nesta rodada;
    - “Coexistência”: rodar `./uninstall.sh` antes do `.deb`; `install.sh` recusa com o pacote
      presente; `uninstall.sh` avisa; `verify.sh` aceita as duas instalações;
    - limitações: daemon em execução continua até o logout após `apt remove`; autostart
      system-wide pode ser desativado com `Hidden=true` em
      `~/.config/autostart/deskawake-*.desktop`; Plasmoid pode exigir novo login.
  - Comandos:
    - `.venv/bin/python -m pytest tests/unit/test_scripts.py -v -k "readme"` ⇒ sem regressão
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "readmes_document_deb"` ⇒ ainda RED para o inglês
  - Critério: todas as seções em pt-BR, comandos com `sudo` apenas no README (nunca nos scripts),
    link para `README.en.md` e para `docs/implementation/spec.md` preservados.
  - Estimativa: 20min

- [ ] **T-24** [R3]: Atualizar `README.en.md`
  - Arquivo: `README.en.md`
  - Equivalência com T-23: “Installation via `.deb` (system-wide)”, `sudo apt install`, update,
    integrity/checksums, coexistence, limitations (`Hidden=true`, logout after remove, Plasmoid
    login).
  - Comandos:
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "readmes_document_deb"` ⇒ GREEN
    - `.venv/bin/python -m pytest tests/unit/test_scripts.py -v -k "readme"` ⇒ sem regressão
  - Critério: os dois READMEs são equivalentes em conteúdo normativo; nenhum comando divergente.
  - Estimativa: 20min

- [ ] **T-25** [R3]: Validar a documentação e o conjunto de testes
  - Comandos:
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py tests/unit/test_scripts.py -v` ⇒ verde
    - `git diff --stat README.md README.en.md` ⇒ apenas as seções novas
  - Critério: os testes antigos de README (comandos normativos, limitações, créditos, link da
    spec) continuam verdes.
  - Estimativa: 5min

### 6. Emenda da spec

- [ ] **T-26** [R3]: Aplicar a emenda da §13 do design em `spec.md`
  - Arquivo: `docs/implementation/spec.md` (apenas docs; não entra no PR de código)
  - Alterações:
    - escopo/§0.1: substituir “O `.deb` via GitHub Releases é a E8 (placeholder); AUR/Flatpak/
      AppImage ficam fora” por “A E8 entrega um `.deb` via GitHub Releases; AUR, Flatpak,
      AppImage e Snap ficam fora”;
    - reprogramação: trocar “E8 = empacotamento/distribuição (placeholder)” por
      “E8 = empacotamento/distribuição (`design_e8.md`)”;
    - decisão 35: acrescentar `packaging/debian/changelog` à lista de arquivos sincronizados com
      `core.__version__`;
    - decisão 38: remover “placeholder até a E7 congelar o layout”, apontar para `design_e8.md` e
      citar `deskawake_0.1.0_all.deb`, `deskawake-0.1.0.tar.gz` e `SHA256SUMS`.
  - Comandos:
    - `grep -n "placeholder" docs/implementation/spec.md` ⇒ apenas ocorrências históricas
      permitidas (nenhuma sobre a E8);
    - `grep -n "packaging/debian/changelog" docs/implementation/spec.md` ⇒ presente na decisão 35;
    - `grep -n "design_e8.md" docs/implementation/spec.md` ⇒ presente na decisão 38/escopo.
  - Critério: apenas `docs/implementation/spec.md` alterado; nada em `docs/implementation/` é
    staged no PR de código.
  - Estimativa: 10min

### 7. Gate, auditoria e PR

- [ ] **T-27** [R3]: Auditar escopo e higiene do pacote
  - Pré-condição: `test_packaging_has_no_spec_paths` já escrito no T-02 (RED → GREEN ao longo das
    tasks de metadados/build).
  - Comandos:
    - `.venv/bin/python -m pytest tests/unit/test_packaging.py -v -k "no_spec_paths"` ⇒ GREEN
    - `grep -RInE "AC-[0-9]|T-[0-9]+|design_e8|tasks_e8|spec\\.md|DELIVERY_MAP|docs/" packaging .github/workflows/release.yml` ⇒ sem saída
    - `find packaging -type f | sort` ⇒ exatamente `build-deb.sh`, `debian/changelog`,
      `debian/control.in`, `debian/copyright`, `test-deb.sh`
    - `git diff --stat -- core ui_gtk plasmoid bin assets data` ⇒ sem saída
  - Critério: nenhum artefato de spec em código; nenhuma mudança no runtime; `packaging/` contém
    apenas os cinco arquivos.
  - Estimativa: 10min

- [ ] **T-28** [R3]: Rodar o gate G-E8 completo
  - Comandos:
    - `for f in install.sh uninstall.sh verify.sh packaging/build-deb.sh packaging/test-deb.sh; do bash -n "$f"; done` ⇒ exit 0
    - `.venv/bin/python -m pytest -q` ⇒ **0 failures, 0 errors** (baseline 398 + novos testes)
    - `packaging/build-deb.sh --allow-dirty` ⇒ exit 0
    - `(cd dist && sha256sum -c SHA256SUMS)` ⇒ dois `OK`
    - `dpkg-deb -I dist/deskawake_0.1.0_all.deb | grep -E 'Package|Version|Architecture|Maintainer|Depends|Suggests'` ⇒ valores do design
    - `dpkg-deb -c dist/deskawake_0.1.0_all.deb | grep -E '__pycache__|docs/|tests/|data/'` ⇒ sem saída
    - `packaging/test-deb.sh` ⇒ exit 0 (install, `status` = 3, remove, sem resíduos, sem daemon)
    - Opcional (não bloqueante): segundo build com `SOURCE_DATE_EPOCH` fixo e comparação do
      SHA-256 do `.deb`.
  - Critério: todos os comandos exit 0; qualquer falha bloqueia o PR. Registrar os resultados no
    corpo do PR. Se o gate rodar **antes** do commit da entrega, o tarball com `--allow-dirty` é do
    `HEAD` antigo e não corresponde ao `.deb`; o release real é sempre construído pelo CI a partir
    da árvore limpa (T-36).
  - Estimativa: 20min

### 8. Checklists manuais por distro

- [ ] **T-29** [R4]: Checklist Mint 22.3 MATE/X11
  - Pré-condição: `dist/deskawake_0.1.0_all.deb` do T-28; máquina Mint 22.3 MATE.
  - Passos:
    - `sudo apt install ./deskawake_0.1.0_all.deb`; conferir `dpkg-query -W deskawake`;
    - `deskawake status` sem daemon ⇒ imprime `off` e sai 3;
    - sair e entrar na sessão; o widget GTK aparece no canto superior direito; o toggle liga/desliga;
      `systemd-inhibit --list` mostra/limpa o DeskAwake;
    - `sudo apt remove deskawake`; sair e entrar; nada reabre; `~/.config/deskawake/` e
      `~/.local/state/deskawake/` preservados; `deskawake` deixa de existir em `/usr/bin`;
    - com o pacote instalado, `./install.sh --only-mate` recusa com a mensagem aprovada (rodar em
      cópia do repo; não usar `sudo`);
    - `./verify.sh` encontra a instalação system-wide;
    - `./uninstall.sh` apenas avisa que o pacote não é removido por ele.
  - Critério: cada item marcado OK ou desvio descrito; resultado colado no PR. Não executar teste
    destrutivo de tampa/suspensão (opcional, fora do gate).
  - Estimativa: 20min

- [ ] **T-30** [R4]: Checklist Kubuntu 26.04 / Plasma 6.6 Wayland
  - Pré-condição: pacote do T-28; máquina Kubuntu.
  - Passos:
    - `sudo apt install ./deskawake_0.1.0_all.deb`;
    - sair e entrar; o Plasmoid aparece em “Adicionar widgets”; adicionar à área de trabalho;
    - toggle liga/desliga e reflete `on/off/error`; `systemd-inhibit --list` mostra/limpa o
      DeskAwake;
    - `sudo apt remove deskawake`; sair e entrar; o Plasmoid some; config/estado preservados;
    - nenhum `kpackagetool6` é executado pelo install/remove (conferir logs do `apt`).
  - Critério: cada item OK ou desvio descrito; resultado no PR. Tampa/suspensão destrutivas ficam
    explicitamente não executadas.
  - Estimativa: 20min

- [ ] **T-31** [R4]: Checklist comum das duas distros
  - Passos:
    - sem daemon, `deskawake status` ⇒ `off`/3; com daemon, `on`/`off` respondem e
      `systemd-inhibit --list` reflete o estado;
    - `sha256sum -c SHA256SUMS` no diretório dos downloads ⇒ OK;
    - `dpkg -I` mostra maintainer, dependências e `Suggests: fonts-inter`;
    - após remoção, nenhum arquivo do pacote permanece em `/usr/lib/deskawake`, `/usr/bin`,
      `/usr/share/dbus-1/services`, `/etc/xdg/autostart` ou `/usr/share/plasma/plasmoids`.
  - Critério: itens não-destrutivos OK; resultado colado no PR. Se uma máquina não estiver
    disponível, registrar a pendência e bloquear o merge (como nas E4–E7).
  - Estimativa: 15min

### 9. Commit, PR, dispatch e release

- [ ] **T-32** [R3]: Preparar commit e PR somente com a entrega de código/docs de usuário
  - Comandos:
    - `git add .gitignore install.sh uninstall.sh verify.sh packaging .github/workflows/release.yml tests/unit/test_packaging.py tests/unit/test_version.py tests/unit/test_scripts.py README.md README.en.md`
    - `git diff --cached --name-only` ⇒ exatamente os 15 caminhos esperados (5 em `packaging/`,
      workflow, 3 scripts, 3 testes, `.gitignore`, 2 READMEs)
    - `git diff --cached --stat -- core ui_gtk plasmoid bin assets data` ⇒ sem saída
    - `git commit -m "feat(e8): empacotamento e distribuição"`
    - `git push -u origin feat/e8-distribuicao`
    - `gh pr create --base main --head feat/e8-distribuicao --title "feat(e8): empacotamento e distribuição" --body "<corpo no template do DELIVERY_MAP>"`
    - `gh pr view --json baseRefName,headRefName,files --jq '{base: .baseRefName, head: .headRefName, files: [.files[].path]}'` ⇒ base `main`, head `feat/e8-distribuicao`, apenas os 15 arquivos
  - Corpo do PR: gate G-E8 com comandos/resultados (pytest, `bash -n`, build, checksums,
    `dpkg-deb`, container, coexistência), checklists manuais T-29–T-31 (executadas ou pendências),
    fora de escopo e riscos residuais do design §14. **Não** citar `spec.md`, `design_e8.md`,
    `tasks_e8.md`, `DELIVERY_MAP.md` nem IDs `AC-*`/`T-*`.
  - Critério: PR contém apenas a entrega; `docs/implementation/` e artefatos de `dist/` fora do
    stage/PR; **nunca** usar `git add -A`/`git add .`.
  - Estimativa: 15min

- [ ] **T-33** [R4]: Aguardar o gate no PR e fazer o merge
  - Comandos:
    - `gh pr checks --watch` ⇒ todos os checks verdes
    - `gh pr view --json mergeable,mergeStateStatus` ⇒ `MERGEABLE`/`CLEAN`
    - `gh pr merge --merge` (merge commit, sem squash; conforme DELIVERY_MAP §0.1)
  - Critério: PR mergeado na `main` com o gate verde; branch `feat/e8-distribuicao` preservada até o
    release; nenhum commit direto na `main`.
  - Estimativa: 5min

- [ ] **T-34** [R4]: Validar o workflow com `workflow_dispatch` na `main`
  - Comandos:
    - `git switch main && git pull`
    - `gh workflow run Release --ref main`
    - `gh run list --workflow release.yml --limit 1 --json databaseId,status,conclusion`
    - `gh run watch <databaseId>` ⇒ `success`
    - `gh run download <databaseId> -n "deskawake-<sha>" -D /tmp/deskawake-e8-artifacts`
    - `ls /tmp/deskawake-e8-artifacts` ⇒ `.deb`, `.tar.gz` e `SHA256SUMS`
    - `(cd /tmp/deskawake-e8-artifacts && sha256sum -c SHA256SUMS)` ⇒ OK
  - Critério: run manual verde, sem publicar release (o `workflow_dispatch` só guarda artefatos);
    os três artefatos baixados conferem com os checksums.
  - Estimativa: 15min

- [ ] **T-35** [R4]: Commit/PR de documentação da spec
  - Arquivos: `docs/implementation/spec.md` (T-26)
  - Comandos:
    - `git switch -c docs/e8-spec-distribuicao`
    - `git add docs/implementation/spec.md`
    - `git commit -m "docs(e8): atualiza a especificação para a distribuição via .deb"`
    - `git push -u origin docs/e8-spec-distribuicao`
    - `gh pr create --base main --head docs/e8-spec-distribuicao --title "docs(e8): distribuição via .deb" --body "Atualiza a spec com as decisões de empacotamento/distribuição da E8."`
    - `gh pr merge --merge`
  - Critério: PR de docs separado do PR de código, contendo apenas `spec.md`; nenhum arquivo de
    `tasks_e8.md`/design é commitado.
  - Estimativa: 10min

- [ ] **T-36** [R4]: Criar a tag `v0.1.0`, acompanhar o release e validar os anexos
  - Pré-condição: T-33/T-34/T-35 concluídas; `core.__version__` = `0.1.0`.
  - Comandos:
    - `git switch main && git pull`
    - `git tag -a v0.1.0 -m "DeskAwake 0.1.0"`
    - `git push origin v0.1.0`
    - `gh run list --workflow release.yml --limit 1 --json databaseId,status,conclusion` e
      `gh run watch <databaseId>` ⇒ `success`
    - `gh release view v0.1.0 --json tagName,assets --jq '{tag: .tagName, assets: [.assets[].name]}'`
      ⇒ exatamente `deskawake_0.1.0_all.deb`, `deskawake-0.1.0.tar.gz`, `SHA256SUMS`
    - baixar os três em `/tmp/deskawake-e8-release` e `sha256sum -c SHA256SUMS`; conferir as notas
      com o comando `sudo apt install ./deskawake_0.1.0_all.deb`
  - Critério: release `v0.1.0` publicado com os três anexos e checksums válidos; nenhum outro
    arquivo anexado; a tag aponta para o commit com a versão `0.1.0`.
  - Estimativa: 15min

- [ ] **T-37** [R4]: Remover os docs transitórios restantes
  - Arquivos: `docs/implementation/DELIVERY_MAP.md` e `docs/implementation/visual/`
  - Comandos:
    - `rm -f docs/implementation/DELIVERY_MAP.md`
    - `rm -rf docs/implementation/visual`
    - `find docs/implementation -type f` ⇒ apenas `tasks_e8.md` (ou o diretório vazio, se este
      arquivo também for removido no encerramento da entrega)
    - `git status --short docs/implementation` ⇒ nenhuma entrada staged
  - Critério: `DELIVERY_MAP.md` e `visual/` fora da árvore local; nada de `docs/` em commit, stage
    ou PR; as remoções são locais e não entram nos PRs de código/docs.
  - Estimativa: 5min

## Mapeamento AC → Tasks

Os critérios vêm do G-E8 (design §10.3), do §10.1/§10.2 e das decisões 1–26 do `design_e8.md`.

| Critério de aceite | Tasks que validam |
|---|---|
| AC-01 — `control.in` com `Package`, `Architecture: all`, maintainer, seis `Depends`, `Suggests`, sem `Recommends`, `Section`/`Priority` e placeholders | T-02, T-03 |
| AC-02 — changelog com topo `deskawake (0.1.0) unstable;` igual a `core.__version__` e maintainer | T-02, T-04, T-05 |
| AC-03 — copyright DEP-5 com linha legal e texto MIT idêntico ao `LICENSE` | T-02, T-06 |
| AC-04 — nenhum maintainer script e `dist/` ignorado | T-02, T-07, T-27 |
| AC-05 — `build-deb.sh` com `dpkg-deb`, `--root-owner-group`, `-Zxz`, `SOURCE_DATE_EPOCH`, `git archive`, `gzip -9n`, `sha256sum`, remoção de `__pycache__` e render de `@EXEC@`; sem `sudo`/`debhelper`/`fpm` | T-08, T-09 |
| AC-06 — nomes `deskawake_0.1.0_all.deb`, `deskawake-0.1.0.tar.gz` e `SHA256SUMS` | T-08, T-09, T-10 |
| AC-07 — build local gera os três artefatos; `sha256sum -c` OK; `dpkg-deb -I/-c` com layout do §3 e sem `__pycache__`/`docs/`/`tests/` | T-10, T-28 |
| AC-08 — `test-deb.sh` com `ubuntu:24.04`, `/pkg`, install/remove e detecção de engine | T-11, T-12 |
| AC-09 — container instala, `deskawake status` = 3, remove, sem resíduos e sem daemon | T-13, T-28 |
| AC-10 — `install.sh` recusa com `dpkg-query`/`/usr/lib/deskawake` e mensagem com `apt remove deskawake` | T-13, T-14, T-15 |
| AC-11 — `uninstall.sh` avisa e remove só o per-user; nunca toca `/usr/*` | T-14, T-16 |
| AC-12 — `verify.sh` resolve `/usr/bin/deskawake` e `/usr/share/dbus-1/services` no fallback | T-14, T-17 |
| AC-13 — workflow com tags `v*`, `workflow_dispatch`, `contents: write`, `ubuntu-latest`, build/test, `gh release`, `upload-artifact`, `SHA256SUMS`, sem `gpg` | T-19, T-20, T-21 |
| AC-14 — `workflow_dispatch` verde na `main`; tag `v0.1.0` publica os três anexos com checksums | T-34, T-36 |
| AC-15 — READMEs pt-BR/inglês com `.deb`, `apt install/remove`, `SHA256SUMS`, atualização, remoção, coexistência e limitações | T-22, T-23, T-24, T-25 |
| AC-16 — nenhum arquivo de `packaging/` cita docs/IDs de spec | T-27 |
| AC-17 — `pytest` completo verde e `bash -n` limpo nos cinco scripts | T-18, T-25, T-28 |
| AC-18 — PR de código só com a entrega; docs em PR separado; nenhuma mudança em `core/`/`ui_gtk/`/`plasmoid/`/`bin/`/`data/` | T-27, T-28, T-32, T-35 |
| AC-19 — layout system-wide do §3 (symlink, `/usr/lib/deskawake`, `/usr/share/...`, autostarts, Plasmoid) | T-10, T-13, T-31 |
| AC-M01 — manual Mint 22.3 MATE: instalar, login, widget/toggle, remover, config preservada, recusa do `install.sh` | T-29 |
| AC-M02 — manual Kubuntu 26.04: instalar, login, Plasmoid em “Adicionar widgets”, toggle, remover | T-30 |
| AC-M03 — manual comum: `status` 0/1/3, `systemd-inhibit --list`, checksums, ausência de resíduos | T-31 |

## Cobertura das decisões do design

| Decisão (design_e8) | Tasks que a fixam |
|---|---|
| 1 — GitHub Releases + `.deb`; CI gera pacote, tarball e checksums | T-19–T-21, T-34, T-36 |
| 2 — `install.sh` per-user continua | T-14, T-15, T-23, T-24 |
| 3 — versão `0.1.0` lida de `core.__version__`, sem override | T-04, T-05, T-09 |
| 4 — AUR/Flatpak/AppImage/Snap/APT/GPG/auto-update fora | T-20, T-21, T-36 |
| 5 — layout system-wide; config/estado por usuário | T-09, T-10, T-13 |
| 6 — pacote único `deskawake`, `Architecture: all` | T-03, T-10 |
| 7 — symlink relativo `/usr/bin/deskawake` | T-09, T-10, T-13 |
| 8 — código em `/usr/lib/deskawake/{core,ui_gtk,assets,bin}` | T-09, T-10 |
| 9 — templates renderizados com `@EXEC@ = /usr/bin/deskawake` | T-09, T-13 |
| 10 — `.service` system-wide | T-09, T-13 |
| 11 — autostarts system-wide (widget com `OnlyShowIn=MATE;`) | T-09, T-13 |
| 12 — Plasmoid em `/usr/share/plasma/plasmoids`, sem `kpackagetool6` | T-09, T-13, T-30 |
| 13 — maintainer aprovado | T-03, T-05, T-06 |
| 14 — `Depends`/`Suggests` aprovados | T-03, T-10 |
| 15 — sem `Recommends` | T-02, T-03 |
| 16 — nenhum maintainer script; install não inicia daemon | T-02, T-12, T-13 |
| 17 — coexistência (`install` recusa, `uninstall` avisa, `verify` aceita) | T-13–T-18 |
| 18 — config/estado preservados na remoção | T-16, T-23, T-24, T-29 |
| 19 — CI `ubuntu-latest` com `dpkg-deb` | T-19, T-20 |
| 20 — artefatos `deskawake_0.1.0_all.deb`, `deskawake-0.1.0.tar.gz`, `SHA256SUMS` | T-08–T-10, T-36 |
| 21 — sem GPG; integridade por SHA-256 | T-20, T-21, T-23, T-36 |
| 22 — teste em `ubuntu:24.04` | T-11–T-13 |
| 23 — update manual, sem auto-update | T-23, T-24 |
| 24 — `packaging/` (não `debian/` na raiz), `release.yml`, `dist/` ignorado | T-07, T-09, T-20, T-27 |
| 25 — READMEs pt-BR/inglês | T-22–T-25 |
| 26 — emenda da spec na implementação (commit `docs:` separado) | T-26, T-35 |

## Notas de execução

1. **RED obrigatório:** em cada task de teste, rodar o comando e confirmar a falha esperada. Não
   avançar para a implementação sem o RED registrado.
2. **`sudo` fora dos scripts:** os testes já existentes proíbem a palavra `sudo` em `install.sh`,
   `uninstall.sh` e `verify.sh`. Use `apt remove deskawake` nas mensagens; `sudo` só aparece nos
   READMEs e nas checklists manuais.
3. **Árvore suja durante a implementação:** este `tasks_e8.md` (e a emenda da spec) deixam
   `git status` sujo. O build local usa `--allow-dirty`; o tarball continua sendo do `HEAD`. Em
   releases/CI a árvore é limpa e o `.deb`/tarball correspondem ao commit.
4. **Não alterar** `core/`, `ui_gtk/`, `plasmoid/`, `bin/`, `assets/`, `data/`, `tests/conftest.py`
   nem o contrato D-Bus. A E8 é empacotamento; qualquer necessidade de código é um achado para
   outro PR.
5. **Docker:** `packaging/test-deb.sh` sai com 2 quando não há `docker`/`podman`. Nesta máquina o
   Docker está funcional; no CI o runner `ubuntu-latest` já o fornece. Se o engine falhar, o gate
   T-28 fica bloqueado.
6. **Reprodutibilidade:** com árvore limpa, `SOURCE_DATE_EPOCH` do commit, mtimes normalizados,
   `root:root`, `gzip -n` e `-Zxz`, dois builds do mesmo commit devem gerar o mesmo SHA-256. A
   comparação é opcional no CI e não bloqueia o gate.
7. **Sem artefatos de spec no código:** `packaging/`, `.github/workflows/release.yml`, scripts e
   testes novos não citam `docs/`, `design_e8.md`, `tasks_e8.md`, `spec.md`, `DELIVERY_MAP.md`,
   `AC-*` ou `T-*`. Os READMEs mantêm apenas o link histórico para a spec exigido pela E7.
8. **PR de código × PR de docs:** o PR `feat/e8-distribuicao` leva código, scripts, workflow,
   testes e READMEs; a emenda da `spec.md` vai em PR `docs:` separado. `docs/implementation/` nunca
   é commitado no PR de código. **Nunca** usar `git add -A`/`git add .`.
9. **Tag só depois do merge:** `v0.1.0` é criada a partir da `main` após o merge do PR de código e
   o `workflow_dispatch` verde. A tag valida `GITHUB_REF_NAME == "v$VERSION"`; não criar tag em
   branch de feature.
10. **Limite do container:** ele não valida GUI, sessão D-Bus real, MATE nem Plasma; essas
    verificações ficam nas checklists manuais T-29–T-31. Se as máquinas não estiverem disponíveis,
    registrar a pendência no PR e bloquear o merge (mesmo critério das E4–E7).
11. **Documento transitório:** este `tasks_e8.md` é o escopo canônico do `/implement`; não entra no
    PR de código nem é citado em código/comentários/commits/PRs.
12. **Limpeza final (T-37):** ao encerrar a R4, remover localmente `DELIVERY_MAP.md` e `visual/`; a
    remoção é local, não vai para stage/commit/PR, e `tasks_e8.md` é o último doc transitório a sair.
