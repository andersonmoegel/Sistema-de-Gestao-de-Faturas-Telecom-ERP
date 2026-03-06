# 📊 Sistema de Gestão de Faturas Telecom (Python)

Aplicação desktop desenvolvida em **Python** para **automação do registro e controle de faturas de operadoras de telecomunicações**.

O sistema realiza:

* 📄 **Leitura automática de PDFs de faturas**
* 🧠 **Extração inteligente de dados**
* 🗃 **Armazenamento estruturado em banco SQLite**
* 📊 **Consulta com filtros avançados**
* ✏️ **Edição e exclusão de registros**
* 📅 **Controle de vencimentos**
* 💰 **Cálculo automático de valores totais**

A interface gráfica foi construída utilizando **CustomTkinter**, com layout inspirado em **sistemas corporativos ERP**.

---

# 🧩 Arquitetura do Sistema

O projeto possui quatro componentes principais:

```
Aplicação
│
├── Interface gráfica (CustomTkinter)
│
├── Motor de Extração de PDFs
│
├── Banco de dados SQLite
│
└── Módulo de consulta e edição
```

Fluxo operacional:

```
PDF da Fatura
     ↓
Extração Inteligente
     ↓
Validação de dados
     ↓
Registro no Banco SQLite
     ↓
Consulta / Filtros / Edição
```

---

# ⚙️ Tecnologias Utilizadas

| Tecnologia    | Função                    |
| ------------- | ------------------------- |
| Python        | Linguagem principal       |
| CustomTkinter | Interface gráfica moderna |
| Tkinter       | Componentes nativos       |
| SQLite        | Banco de dados local      |
| Pandas        | Manipulação de dados      |
| PDFPlumber    | Extração de texto de PDFs |
| tkcalendar    | Seleção de datas          |
| Regex (re)    | Processamento de texto    |

---

# 📦 Dependências

Instale as bibliotecas necessárias:

```bash
pip install customtkinter pdfplumber pandas tkcalendar
```

Bibliotecas padrão utilizadas:

```
os
re
sqlite3
datetime
tkinter
```

---

# 🗄 Estrutura do Banco de Dados

O sistema utiliza **SQLite local**.

Arquivo gerado automaticamente:

```
telecom_shared.db
```

Tabela principal:

## `faturas`

| Campo      | Tipo    | Descrição                           |
| ---------- | ------- | ----------------------------------- |
| id         | INTEGER | Identificador único                 |
| empresa    | TEXT    | Código da empresa                   |
| operadora  | TEXT    | Nome da operadora                   |
| mes_ano    | TEXT    | Referência da fatura                |
| valor      | REAL    | Valor da fatura                     |
| vencimento | TEXT    | Data de vencimento                  |
| data_envio | TEXT    | Data de registro no sistema         |
| ritm       | TEXT    | Número de chamado                   |
| nf_servico | TEXT    | Indica se possui NF                 |
| usuario    | TEXT    | Usuário responsável pelo lançamento |

---

# 🤖 Motor de Extração Inteligente

O sistema possui um **módulo de leitura automática de PDFs** utilizando `pdfplumber`.

A função principal é:

```python
extrair_inteligente(caminho_arquivo)
```

Ela identifica automaticamente:

* Operadora
* Empresa (via CNPJ)
* Valor da fatura
* Data de vencimento

---

## 🧠 Estratégias de Extração

### 1️⃣ Identificação da Operadora

O sistema verifica o nome do arquivo:

```
CLARO_FATURA.pdf
TIM_123456.pdf
VIVO_JANEIRO.pdf
```

Comparando com a lista:

```python
OPERADORAS = [
ALGAR, ATHENA, BITWAVE, BRDIGITAL,
CLARO, EMBRATEL, FENIX, GNET,
GWM, INVISTA, MUNDIVOX, NORTE TELECOM,
OI, ORANGE, SIM FIBRA, TIM,
UNIFIQUE, VIVO
]
```

---

### 2️⃣ Identificação da Empresa via CNPJ

O sistema busca **CNPJs dentro do PDF** usando regex:

```python
\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}
```

Depois cruza com o mapa:

```python
MAPA_CNPJ = {
    "12345678000123": "1001",
    ...
}
```

Convertendo o CNPJ em **código da empresa**.

---

### 3️⃣ Captura do Valor da Fatura

O sistema busca valores próximos a palavras-chave:

```
TOTAL A PAGAR
VALOR TOTAL
TOTAL DESTA FATURA
VALOR LÍQUIDO
```

Regex usada:

```
(\d{1,3}(?:\.\d{3})*,\d{2})
```

Caso não encontre:

* captura todos os valores do início do PDF
* seleciona o **maior valor encontrado**

---

### 4️⃣ Captura de Data de Vencimento

Busca datas no formato:

```
dd/mm/aaaa
```

Regex:

```
\d{2}/\d{2}/\d{4}
```

E filtra apenas datas válidas entre:

```
2024 — 2030
```

---

# 🖥 Interface do Sistema

A aplicação possui **3 módulos principais**.

---

# 1️⃣ Tela Principal

Funções:

* Importar PDF da fatura
* Conferir dados extraídos
* Inserir RITM
* Marcar presença de NF
* Salvar registro

Fluxo:

```
Selecionar PDF
     ↓
Auto extração
     ↓
Revisão manual
     ↓
Salvar registro
```

---

# 2️⃣ Painel de Consulta

Tela de controle com filtros:

Filtros disponíveis:

* Empresa
* Operadora
* Mês
* Ano
* Número de RITM

A tabela exibe:

```
Empresa
Operadora
Referência
Valor
Vencimento
Envio
NF
RITM
Status
Usuário
```

---

# 🚦 Indicadores de Status

O sistema calcula automaticamente:

| Status      | Condição          |
| ----------- | ----------------- |
| 🟢 NO PRAZO | vencimento ≥ hoje |
| 🔴 VENCIDO  | vencimento < hoje |

---

# ✏️ Tela de Edição

Ao **clicar duas vezes em um registro**, abre a tela de gerenciamento.

Permite:

* Alterar empresa
* Alterar operadora
* Corrigir valor
* Alterar vencimento
* Editar RITM
* Atualizar presença de NF

Também é possível:

```
Excluir registro
```

---

# 📂 Estrutura de Arquivos Recomendada

```
telecom-faturas/
│
├── app.py
├── telecom_shared.db
├── README.md
└── requirements.txt
```

---

# ▶️ Como Executar o Sistema

1️⃣ Clone o repositório

```bash
git clone https://github.com/seuusuario/telecom-faturas.git
```

2️⃣ Instale dependências

```bash
pip install -r requirements.txt
```

3️⃣ Execute o sistema

```bash
python app.py
```

---

# 🔐 Controle de Usuário

O sistema registra automaticamente o usuário da máquina:

```python
USUARIO_MAQUINA = os.getlogin()
```

Este valor é armazenado no campo:

```
usuario
```

---

# 📈 Possíveis Melhorias Futuras

Sugestões de evolução do sistema:

* Dashboard financeiro
* Gráficos de custos por operadora
* Exportação para Excel
* Importação em lote de PDFs
* Integração com ServiceNow (RITM)
* OCR para PDFs escaneados
* Versão executável (.exe)
* Banco de dados corporativo (PostgreSQL)

---

# 📄 Licença

Este projeto pode ser utilizado para **fins corporativos e educacionais**.

---

