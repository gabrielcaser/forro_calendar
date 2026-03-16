# 🎵 Forró Calendar Automation

Automatiza a leitura da agenda de bailes de forró do Instagram **@lelele_godoy**, exporta para Excel e adiciona os eventos ao **Google Calendar** num calendário dedicado, toda terça-feira às 8h.

---

## Como funciona

1. O **Windows Task Scheduler** dispara o script toda **terça às 8h**
2. O script busca no Instagram o post com a palavra-chave **"agenda de forró"**
3. Baixa as fotos do post (cartazes com a agenda)
4. Envia as fotos para o **GPT-4o Vision** que lê os eventos de todos os dias da semana
5. Exporta os eventos para um arquivo **Excel** em `output/`
6. Pergunta interativamente se deve adicionar os eventos ao **Google Calendar "🎵 Forró DF"**
7. Evita duplicatas: posts já processados são ignorados; eventos já existentes no Calendar são pulados

---

## Pré-requisitos

- Python 3.9 ou superior
- Conta Google com Google Calendar habilitado
- Chave de API da OpenAI (`gpt-4o-mini`)
- Conta no Instagram (para autenticação)

---

## Estrutura do projeto

```
forro_calendar/
├── main.py                      # Orquestrador principal (interativo)
├── run_excel_only.py            # Extrai eventos sem tocar no Calendar
├── run.bat                      # Entrada do Task Scheduler
├── requirements.txt
├── .env                         # Credenciais (não versionado)
├── .env.example                 # Template
├── google_credentials.json      # OAuth Google (não versionado)
├── token.json                   # Token gerado automaticamente
├── instagram_session-<user>     # Sessão Instagram salva (não versionado)
│
├── src/
│   ├── config.py                # Constantes e caminhos centralizados
│   ├── utils.py                 # Controle de posts processados
│   ├── instagram.py             # Scraping via web_profile_info endpoint
│   ├── vision.py                # Extração de eventos com GPT-4o Vision
│   ├── calendar_sync.py         # Integração Google Calendar
│   └── excel_export.py          # Geração e leitura de planilha Excel
│
├── data/
│   ├── processed_posts.json     # Posts já processados (auto-gerado)
│   ├── calendar_id.txt          # ID do calendário "🎵 Forró DF" (auto-gerado)
│   └── temp_images/             # Imagens temporárias (limpo após uso)
│
├── output/
│   └── forro_agenda_YYYY-MM-DD.xlsx   # Planilha exportada
│
└── logs/
    └── forro_calendar.log       # Log de execuções
```

---

## Setup (faça uma vez só)

### 1. Clonar e instalar dependências

```powershell
git clone https://github.com/gabrielcaser/forro_calendar.git
cd forro_calendar

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

### 2. Configurar variáveis de ambiente

```powershell
Copy-Item .env.example .env
```

Abra `.env` e preencha:

```env
OPENAI_API_KEY=sk-SuaChaveAqui
INSTAGRAM_USERNAME=seu_usuario
INSTAGRAM_PASSWORD=sua_senha
```

> **OpenAI:** Acesse [platform.openai.com/api-keys](https://platform.openai.com/api-keys).  
> O custo é mínimo — cada execução usa alguns centavos com `gpt-4o-mini`.

---

### 3. Configurar credenciais do Google Calendar

**a) Criar projeto no Google Cloud:**

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um novo projeto (ex.: `forro-calendar`)
3. **APIs e serviços → Biblioteca** → Busque **Google Calendar API** → Ativar

**b) Criar credenciais OAuth:**

1. **APIs e serviços → Credenciais → + Criar credenciais → ID do cliente OAuth**
2. Tipo: **App para computador**
3. Baixe o JSON e renomeie para `google_credentials.json` na raiz do projeto

**c) Adicionar usuário de teste (se o app ainda está em modo de teste):**

1. **APIs e serviços → Tela de permissão OAuth → Usuários de teste**
2. Adicione o e-mail da sua conta Google

**d) Autorizar (primeira execução):**

```powershell
.\venv\Scripts\python.exe main.py
```

O navegador abrirá pedindo autorização. Clique em **Permitir**.  
O arquivo `token.json` é salvo automaticamente para execuções futuras.

---

### 4. Agendar execução toda terça às 8h

Execute no **PowerShell como Administrador**:

```powershell
$action   = New-ScheduledTaskAction -Execute "C:\caminho\para\forro_calendar\run.bat"
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At "08:00AM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName "ForroCalendar" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Description "Busca agenda de forro no Instagram e adiciona ao Google Calendar"
```

Para testar manualmente:
```powershell
Start-ScheduledTask -TaskName "ForroCalendar"
```

---

## Uso interativo

Ao rodar `main.py` manualmente:

```
Post DVtwGYPiV_O já foi processado anteriormente. Continuar mesmo assim? [s/N]
Excel de hoje já existe (forro_agenda_2026-03-15.xlsx). Extrair novamente e substituir? [s/N]
5 evento(s) disponível(is). Criar no Google Calendar? [s/N]
```

### `run_excel_only.py`
Extrai eventos e gera o Excel sem tocar no Google Calendar — útil para testes.

---

## Formato do Excel exportado

| Dia | Data | Hora início | Hora fim | Local | Descrição |
|---|---|---|---|---|---|
| Sexta | 13/03 | 20:00 | 00:00 | Clube do CBMDF | ... |
| Sábado | 14/03 | 19:00 | 23:00 | Infinu (506s) | ... |

- **Hora fim** é calculada como início + 4h quando não informada no cartaz
- A planilha inclui uma linha de rodapé com a data/hora de extração

---

## Solução de problemas

| Problema | Solução |
|---|---|
| `OPENAI_API_KEY não configurada` | Verifique o arquivo `.env` |
| `google_credentials.json não encontrado` | Siga o passo 3 acima |
| `Error 403 access_denied` | Adicione seu e-mail como usuário de teste no Google Cloud Console |
| Instagram bloqueando acesso | A sessão é salva em `instagram_session-<user>`; na primeira execução seu usuário/senha do `.env` são usados |
| Eventos duplicados no Calendar | O script verifica duplicatas por data+local antes de inserir |
| Eventos de dias passados não criados | A janela padrão aceita eventos de até 7 dias no passado |

---

## Logs

```
logs/forro_calendar.log
```


---

## Como funciona

1. O **Windows Task Scheduler** dispara o script toda **terça às 8h**
2. O script busca no Instagram o post com o texto **"Agenda bailes de forró (DF)"**
3. Baixa as fotos do post (cartazes com a agenda)
4. Envia as fotos para o **GPT-4o Vision** que lê os eventos
5. Adiciona automaticamente os eventos de **sexta, sábado e domingo** ao seu Google Calendar
6. Evita duplicatas: posts já processados são ignorados nas semanas seguintes

---

## Pré-requisitos

- Python 3.11 ou superior
- Conta Google com Google Calendar
- Chave de API da OpenAI (para leitura das imagens via IA)

---

## Setup (faça uma vez só)

### 1. Instalar dependências Python

Abra o PowerShell **como Administrador** e rode:

```powershell
cd C:\Users\gabri\forro_calendar

# Criar ambiente virtual
python -m venv venv

# Ativar
.\venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt
```

---

### 2. Configurar variáveis de ambiente

```powershell
# Na pasta forro_calendar, copie o exemplo:
Copy-Item .env.example .env
```

Abra o arquivo `.env` e preencha:

```
OPENAI_API_KEY=sk-SuaChaveAqui
```

> **Onde obter a chave OpenAI:**  
> Acesse [platform.openai.com/api-keys](https://platform.openai.com/api-keys), crie uma chave e cole aqui.  
> O custo é mínimo — cada execução usa centavos de dólar com `gpt-4o-mini`.

---

### 3. Configurar credenciais do Google Calendar

**a) Criar projeto no Google Cloud:**

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um novo projeto (ex.: `forro-calendar`)
3. No menu lateral: **APIs e serviços → Biblioteca**
4. Busque **Google Calendar API** e clique em **Ativar**

**b) Criar credenciais OAuth:**

1. Vá em **APIs e serviços → Credenciais**
2. Clique em **+ Criar credenciais → ID do cliente OAuth**
3. Tipo de aplicativo: **App para computador**
4. Nome: `forro-calendar` (qualquer nome)
5. Clique em **Criar** → **Baixar JSON**
6. Renomeie o arquivo baixado para `google_credentials.json`
7. Mova para `C:\Users\gabri\forro_calendar\google_credentials.json`

**c) Autorizar o acesso (uma única vez):**

```powershell
cd C:\Users\gabri\forro_calendar
.\venv\Scripts\Activate.ps1
python main.py
```

Na primeira execução, o navegador vai abrir pedindo autorização. Clique em **Permitir**.  
Após isso, o arquivo `token.json` é salvo e não precisa mais de interação manual.

---

### 4. Agendar execução toda terça às 8h

Rode este comando no **PowerShell como Administrador**:

```powershell
$action  = New-ScheduledTaskAction -Execute "C:\Users\gabri\forro_calendar\run.bat"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At "08:00AM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName "ForroCalendar" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Description "Busca agenda de forro no Instagram e adiciona ao Google Calendar"
```

Para confirmar que foi criado:
```powershell
Get-ScheduledTask -TaskName "ForroCalendar"
```

Para testar manualmente agora:
```powershell
Start-ScheduledTask -TaskName "ForroCalendar"
```

---

## Estrutura de arquivos

```
forro_calendar/
├── main.py                  # Script principal
├── requirements.txt         # Dependências Python
├── run.bat                  # Chamado pelo Task Scheduler
├── .env                     # Suas chaves de API (não compartilhe!)
├── .env.example             # Template do .env
├── google_credentials.json  # Credenciais OAuth do Google (não compartilhe!)
├── token.json               # Token de acesso (gerado automaticamente)
├── processed_posts.json     # Posts já processados (gerado automaticamente)
└── forro_calendar.log       # Log de execuções (gerado automaticamente)
```

---

## Solução de problemas

| Problema | Solução |
|---|---|
| `OPENAI_API_KEY não configurada` | Verifique o arquivo `.env` |
| `google_credentials.json não encontrado` | Siga o passo 3 acima |
| Instagram bloqueando acesso | Adicione suas credenciais do Instagram no `.env` |
| Evento não encontrado | Verifique se o post já existe no Instagram com o texto exato |
| Eventos duplicados | O script verifica duplicatas automaticamente |

---

## Logs

Acompanhe as execuções em:
```
C:\Users\gabri\forro_calendar\forro_calendar.log
```
