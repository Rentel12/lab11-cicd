# lab11-cicd

Небольшое Flask-приложение для практики CI/CD с GitHub Actions. На каждом Pull Request выполняются lint, тесты на Python 3.11 и 3.12 и проверка истории на секреты. При push в `main` или тега `v*` workflow дополнительно собирает Docker-образ, проверяет его Trivy и публикует в GitHub Container Registry (GHCR).

## Структура

```text
.
├── .github/workflows/ci.yml
├── tests/test_app.py
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── Dockerfile
├── .dockerignore
├── .gitignore
└── .trivyignore
```

## Требования

- Python 3.12 для локальной работы по заданию (CI также проверяет Python 3.11).
- Git.
- Docker Desktop с запущенным Docker Engine для сборки и запуска контейнеров.
- GitHub account для публикации репозитория и образа.

## Локальная настройка (Windows PowerShell)

Из корневой папки проекта:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Если политика PowerShell блокирует активацию, можно не менять системную политику, а вызывать интерпретатор напрямую:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Проверки

```powershell
ruff check .
ruff format --check .
pytest -q
```

Чтобы применить форматирование Ruff:

```powershell
ruff format .
```

Тесты проверяют `greet`, `/healthz` и значение по умолчанию для `/version`.

## API

| Метод | Путь | Результат |
|---|---|---|
| GET | `/` | JSON с именем хоста и greeting |
| GET | `/healthz` | `{"status":"ok"}` |
| GET | `/version` | `{"version":"dev"}` либо значение `APP_VERSION` |

Приложение слушает порт `8000`. Версию можно задать переменной окружения `APP_VERSION`.

## Docker

Сборка и запуск локального образа:

```powershell
docker build --build-arg APP_VERSION=dev -t lab11-app:local .
docker run --rm -d --name lab11-local -p 8011:8000 lab11-app:local
Invoke-RestMethod http://localhost:8011/healthz
Invoke-RestMethod http://localhost:8011/version
docker rm -f lab11-local
```

Контейнер работает от непривилегированного пользователя `appuser`; Docker health check проверяет `/healthz`. `APP_VERSION` задаётся build argument-ом и становится environment variable внутри контейнера.

## GitHub Actions и безопасность

`.github/workflows/ci.yml` использует версии Actions и инструменты, указанные в задании:

- `lint`: Ruff lint и проверка форматирования на Python 3.12.
- `test`: матрица Python 3.11/3.12, JUnit XML и отдельный artifact на каждую версию; загрузка отчёта выполняется и при падении теста.
- `secrets-scan`: Gitleaks `v8.30.1` сканирует полную Git-историю.
- `image`: только для событий `push`, после успешных проверок; собирает образ, запускает Trivy на HIGH/CRITICAL findings и публикует прошедший проверку образ. `packages: write` выдано только этому job.

Trivy пропускает неустранённые уязвимости (`ignore-unfixed: true`), но блокирует сборку при найденных исправимых HIGH/CRITICAL уязвимостях (`exit-code: "1"`). Не добавляйте CVE в `.trivyignore` без проверки, причины, владельца и срока пересмотра.

## Настройка репозитория и Pull Request

Создайте на GitHub **публичный** репозиторий `lab11-cicd` без README. После этого из корневой папки проекта выполните в PowerShell (замените имя на свой GitHub username):

```powershell
$GitHubUser = "your-github-username"
git init -b main
git add app.py tests/ requirements.txt requirements-dev.txt pyproject.toml Dockerfile .dockerignore .gitignore .trivyignore README.md
git commit -m "feat: lab11 app with tests"
git remote add origin "https://github.com/$GitHubUser/lab11-cicd.git"
git push -u origin main
```

Это единственная начальная отправка напрямую в `main`; после настройки правил используйте Pull Request. Для CI branch и PR:

```powershell
git switch -c ci
git add .github/workflows/ci.yml
git commit -m "ci: lint, test matrix, secret scan, image"
git push -u origin ci
```

Так workflow добавляется в PR, а не в начальный commit. На GitHub откройте PR `ci` → `main`. Временно уберите `.strip()` в `greet`, сохраните, затем:

```powershell
git add app.py
git commit -m "refactor: simplify greet"
git push
```

Дождитесь красных `test (3.11)` и `test (3.12)` в PR, откройте упавший `test_greet` и скачайте JUnit artifacts. Верните `.strip()` и отправьте исправление:

```powershell
git revert HEAD
git push
```

Убедитесь, что проверки того же PR стали зелёными. Не сливайте PR до завершения остальных настроек задания.

### Защита ветки `main`

После первого запуска workflow откройте **Settings → Rules → Rulesets → New branch ruleset**:

1. Имя: `protect-main`, Enforcement: **Active**, target: default branch; оставьте список обхода правил (bypass) пустым.
2. Включите **Restrict deletions** и **Block force pushes**.
3. Включите **Require a pull request before merging** (для одиночной учебной работы допустимо 0 approvals).
4. Включите **Require status checks to pass** и добавьте имена точно как в Checks: `lint`, `test (3.11)`, `test (3.12)`, `secrets-scan`.

До первого выполнения workflow эти checks могут не появляться в списке. Убедитесь в GitHub, что ruleset активен; локальная конфигурация этого не подтверждает.

## Публикация и релиз

При push в `main` metadata-action формирует `main` и `sha-…`; при push semver-тега `v1.0.0` создаёт тег образа `1.0.0` (без начальной `v`). Используется lowercase-имя `ghcr.io/<github-user>/lab11-cicd`.

После успешного запуска в GitHub Actions проверьте package в **Profile → Packages**. Если GHCR запрещает скачивание, сделайте package публичным в Package settings. Не публикуйте секреты; workflow использует краткоживущий `GITHUB_TOKEN`.

Пример команд для релиза (в PowerShell, после настройки remote и с актуальной `main`):

```powershell
$GitHubUser = "your-github-username"
$Image = "ghcr.io/$($GitHubUser.ToLowerInvariant())/lab11-cicd"
git switch main
git pull
git tag v1.0.0
git push origin v1.0.0
docker pull "${Image}:1.0.0"
docker run --rm -d --name lab11 -p 8011:8000 "${Image}:1.0.0"
Invoke-RestMethod http://localhost:8011/version
docker rm -f lab11
```

Ожидаемая версия в ответе — `1.0.0`. Эти команды публикации и скачивания выполняются после создания GitHub-репозитория и успешной CI-публикации.

## Stretch: deploy и rollback

Задание предлагает optional deploy workflow с ручным approval в GitHub Environment `production`, SSH на Linux VM либо self-hosted runner. В этом проекте stretch не включён: для него нужны инфраструктура и секреты, а self-hosted runner небезопасно использовать с PR в публичном репозитории. Не добавляйте реальные ключи в репозиторий. При наличии подготовленной VM deploy можно настроить отдельно по инструкциям Part D в PDF; workflow принимает тег образа и может повторно развернуть `1.0.0` для rollback.

## Что проверить для сдачи

- PR: красный запуск из-за `test_greet`, JUnit artifacts, исправляющий commit и зелёный запуск того же PR.
- Checks и активный ruleset для `main`.
- Run на `main` и run тега `v1.0.0`; package в GHCR с тегами `main`, `sha-…`, `1.0.0`.
- Trivy findings и способ их разрешения: исправление или обоснованное исключение в `.trivyignore`.
- Запуск опубликованного `1.0.0` образа и ответ `/version`.
- При устном ответе будьте готовы объяснить CI/CD, триггеры job-ов, matrix/cache, `GITHUB_TOKEN` и permissions, Docker metadata tags, Trivy gate, branch protection и (если делали stretch) ручное approval и rollback.

## Короткие ответы для устной защиты

1. **Чем отличаются CI, continuous delivery и continuous deployment?** CI автоматически проверяет изменения. Continuous delivery готовит проверенный артефакт к выпуску. Continuous deployment автоматически выкладывает его в рабочую среду. Здесь реализованы CI и сборка/публикация артефакта; production deployment — только optional stretch.
2. **Что запускает jobs?** Pull Request запускает `lint`, два варианта `test` и `secrets-scan`. Push в `main` или `v*` запускает те же проверки, а затем `image`. На PR публикация не выполняется из-за `if: github.event_name == 'push'`.
3. **Зачем matrix и pip cache?** Matrix повторяет тесты с разными версиями Python. Pip cache ускоряет последующие установки зависимостей.
4. **Зачем permissions и что такое `GITHUB_TOKEN`?** Workflow по умолчанию имеет только `contents: read`; `packages: write` выдаётся только job публикации. `GITHUB_TOKEN` — временный токен GitHub Actions для разрешённых операций с репозиторием и package.
5. **Какие tags создаются?** Для `main` — `main` и `sha-…`; для git-тега `v1.0.0` — Docker-тег `1.0.0`. Релизную версию удобно разворачивать по semver-тегу.
6. **Что делает Trivy gate?** Сканирует собранный образ на HIGH/CRITICAL уязвимости. Исправимые находки блокируют публикацию; исключение допустимо лишь с обоснованием и владельцем в `.trivyignore`.
7. **Как branch protection запрещает merge?** GitHub не разрешает слить PR, пока все обязательные checks не завершились успешно; требование PR не даёт напрямую внести изменения в `main`.
8. **Что добавляет production environment и как работает rollback?** Environment может приостановить deploy до ручного approval и хранить deployment secrets. Rollback повторно запускает deploy с уже опубликованным старым image tag, поэтому образ не нужно пересобирать.
