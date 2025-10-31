# MVP Local - Gestão de Slots e Picking

Sistema offline para gestão de slots e picking de devices com alocação automática e planejamento de coleta otimizado.

## 🚀 Stack

- **Backend**: Python 3.11+, FastAPI
- **DB**: SQLite (storage/app.db) usando SQLAlchemy + Alembic
- **UI**: FastAPI + Jinja2 + HTMX + Tailwind via CDN (sem build step)
- **Execução**: uvicorn main:app --reload

## 📋 Pré-requisitos

- Python 3.11 ou superior
- pip

## 🛠️ Setup Rápido

```bash
# 1. Criar ambiente virtual
python -m venv .venv

# 2. Ativar ambiente virtual
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar arquivo .env (opcional)
# Criar arquivo .env na raiz com:
# DATABASE_URL=sqlite:///./storage/app.db
# CUSTO_MUDAR_RUA=10
# CUSTO_MUDAR_PRATELEIRA=5
# CUSTO_POR_LINHA=1
# CUSTO_POR_COLUNA=1
# START_RUA=1
# START_PRATELEIRA=P1
# START_LINHA=1
# START_COLUNA=1

# 5. Rodar migrations do Alembic
alembic upgrade head

# 6. Popular banco com topologia fixa
python seed.py

# 7. Iniciar servidor
uvicorn main:app --reload
```

O servidor estará disponível em: http://localhost:8000

## 📁 Estrutura do Projeto

```
picking_solution/
├── alembic/                  # Migrations do Alembic
│   ├── versions/            # Arquivos de migração
│   ├── env.py              # Configuração do Alembic
│   └── script.py.mako      # Template de migração
├── models/                  # Models SQLAlchemy
│   ├── aisle.py           # Model de Ruas
│   ├── shelf.py           # Model de Prateleiras
│   ├── slot.py            # Model de Slots
│   ├── device.py          # Model de Devices
│   ├── movement.py        # Model de Movimentos (auditoria)
│   └── database.py        # Configuração do banco
├── schemas/                 # Schemas Pydantic
│   ├── assignment_schemas.py
│   ├── picking_schemas.py
│   ├── scan_schemas.py
│   ├── slot_schemas.py
│   └── device_schemas.py
├── services/                # Serviços de negócio
│   ├── distance_service.py  # Cálculo de distância Manhattan
│   ├── assignment_service.py # Alocação automática
│   └── picking_service.py   # Picking com Nearest Neighbor + 2-opt
├── routers/                 # Rotas FastAPI
│   ├── slots.py            # Rotas de slots
│   ├── assign.py           # Rotas de alocação
│   ├── picking.py          # Rotas de picking
│   ├── scan.py             # Rotas de scan IN/OUT
│   └── devices.py          # Rotas de devices
├── templates/               # Templates Jinja2
│   ├── base.html           # Template base
│   ├── index.html          # Dashboard
│   ├── assign.html         # Página de alocação
│   ├── picking.html        # Página de picking
│   ├── available_slots.html # Página de slots livres
│   ├── search.html         # Página de consulta
│   └── partials/           # Templates parciais HTMX
│       ├── assign_result.html
│       ├── picking_result.html
│       ├── slots_result.html
│       └── search_result.html
├── storage/                 # Banco de dados SQLite (gerado)
├── main.py                  # Aplicação FastAPI principal
├── seed.py                  # Script para popular banco
├── alembic.ini             # Configuração do Alembic
├── requirements.txt         # Dependências Python
└── README.md               # Este arquivo
```

## 🏗️ Topologia Fixa

O sistema usa uma topologia fixa:

- **RUA 1**: 1 prateleira na esquerda (P1)
- **RUA 2**: 2 prateleiras (P1 esquerda, P2 direita)
- **RUA 3**: 1 prateleira na direita (P1)
- **Cada prateleira**: 24 linhas (horizontal) × 40 slots (horizontal) = 960 slots
- **Total: 3.840 slots** (4 prateleiras × 960 = 3.840)

Código humano do slot: `R{rua}-P{prateleira}-L{linha}-C{coluna}`

Exemplo: `R1-P1-L1-C1`, `R2-P1-L1-C1`, `R2-P2-L1-C1`, `R3-P1-L1-C1`

## 🎯 Funcionalidades

### 1. Dashboard
- Visão geral: totais de slots, slots livres, devices em estoque
- Últimos movimentos registrados

### 2. Alocação Automática
- Recebe lista de device_ids (textarea ou upload CSV)
- Aloca devices em slots livres usando algoritmo guloso (sempre ao slot livre mais próximo)
- Atualiza posição atual após cada alocação
- Registra movimentos para auditoria

### 3. Picking (Coleta)
- Recebe lista de device_ids (textarea ou upload CSV)
- Calcula ordem de coleta usando Nearest Neighbor + 2-opt simples
- Exporta plano para CSV
- Permite dar baixa por bip (campo sempre focado para digitar/escanear Device ID)
- Marca devices como "PICKED" ao coletar

### 4. Slots Livres Próximos
- Lista slots livres ordenados pelo percurso mais curto
- Permite configurar ponto de partida
- Ordenação por distância Manhattan com custos configuráveis

### 5. Scan IN/OUT
- **Scan IN**: Faz entrada de device (aloca automaticamente se não informado slot)
- **Scan OUT**: Faz saída de device (libera slot)
- Ambos registram movimentos para auditoria

### 6. Consulta
- Busca por device_id ou human_code do slot
- Mostra posição, status e informações do device

## 📐 Cálculo de Distância

A distância é calculada usando **Manhattan** com custos configuráveis:

- `CUSTO_MUDAR_RUA`: 10 (padrão)
- `CUSTO_MUDAR_PRATELEIRA`: 5 (padrão)
- `CUSTO_POR_LINHA`: 1 (padrão)
- `CUSTO_POR_COLUNA`: 1 (padrão)

Valores podem ser configurados no arquivo `.env`.

## 🔧 Configuração (.env)

Crie um arquivo `.env` na raiz do projeto:

```env
# Database
DATABASE_URL=sqlite:///./storage/app.db

# Distance costs
CUSTO_MUDAR_RUA=10
CUSTO_MUDAR_PRATELEIRA=5
CUSTO_POR_LINHA=1
CUSTO_POR_COLUNA=1

# Default start position
START_RUA=1
START_PRATELEIRA=P1
START_LINHA=1
START_COLUNA=1
```

## 📊 Endpoints API

### Slots
- `GET /slots/available` - Lista slots livres (JSON)
- `GET /slots/page` - Página HTML de slots livres

### Alocação
- `POST /assign/auto` - Aloca devices automaticamente (JSON)
- `POST /assign/auto/htmx` - Aloca devices (HTML/HTMX)

### Picking
- `POST /picking/plan` - Cria plano de picking (JSON)
- `POST /picking/plan/htmx` - Cria plano de picking (HTML/HTMX)
- `GET /picking/plan.csv` - Exporta plano em CSV
- `POST /picking/mark-picked` - Marca device como coletado

### Scan
- `POST /scan/in` - Scan IN (entrada)
- `POST /scan/out` - Scan OUT (saída)

### Devices
- `GET /devices/{device_id}` - Busca device por ID
- `GET /devices/search/query` - Busca devices (JSON)
- `GET /devices/search/htmx` - Busca devices (HTML/HTMX)

## 🧪 Testes

Para rodar testes (se implementados):

```bash
pytest
```

## 📝 Migrations

Para criar uma nova migration:

```bash
alembic revision --autogenerate -m "Descrição da mudança"
alembic upgrade head
```

## 🔄 Reset do Banco

Para resetar o banco e popular novamente:

```bash
python seed.py --force
```

## 🎨 UI

A interface usa:
- **Tailwind CSS** via CDN (sem build step)
- **HTMX** para atualizações dinâmicas sem recarregar página
- **Jinja2** para templates server-side

## 📈 Performance

- Alocação de 50 devices: < 2s em máquina local comum
- Picking de 50 devices: < 2s (Nearest Neighbor + 2-opt limitado a 200 iterações ou 2s máx)
- Todas as operações usam transações para garantir atomicidade

## 🐛 Troubleshooting

### Erro: "No module named 'models'"
Certifique-se de estar executando do diretório raiz do projeto.

### Erro: "sqlite3.OperationalError: database is locked"
Feche outras conexões ao banco ou reinicie o servidor.

### Banco não foi criado
Execute: `alembic upgrade head && python seed.py`

## 📄 Licença

Este é um projeto MVP para uso local/offline.

---

**Desenvolvido para MVP local offline - Simplicidade e startup rápido**

