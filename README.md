# Rating Mock

Ferramenta CLI para geração de dados mockados de rating e enriquecimento de crédito a partir de arquivos de referência de bureaus, com suporte a publicação automatizada nos buckets S3 do Datalake.

O utilitário é totalmente compatível tanto com o formato tradicional numérico quanto com o novo **CNPJ Alfanumérico** da Receita Federal.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Bureaus e Destinos](#bureaus-e-destinos)
- [Ambientes S3](#ambientes-s3)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
  - [1. Gerar mocks apenas localmente](#1-gerar-mocks-apenas-localmente)
  - [2. Simular upload no S3 (--dry-run)](#2-simular-upload-no-s3---dry-run)
  - [3. Gerar e publicar no S3](#3-gerar-e-publicar-no-s3)
  - [4. Publicar no S3 sem manter cópia local](#4-publicar-no-s3-sem-manter-cópia-local)
- [Suporte a CNPJ Alfanumérico](#suporte-a-cnpj-alfanumérico)
- [Estrutura do Projeto](#estrutura-do-projeto)

---

## Visão Geral

O script `generate_mock.py` toma como base um conjunto de arquivos JSON de referência na pasta `json/` (gerados a partir de um CNPJ semente `00009838000146`).

A partir de um novo CNPJ informado pelo usuário:
1. Normaliza o CNPJ (remove pontuações/máscara, converte para maiúsculas e valida se possui 14 caracteres).
2. Substitui o CNPJ original em todos os arquivos de referência.
3. Grava os novos arquivos na pasta `output/<CNPJ>/`.
4. Opcionalmente publica diretamente no S3 no prefixo e ambiente configurados (`dev`, `stg` ou `prd`).

---

## Bureaus e Destinos

| Sufixo do Arquivo | Bureau | Prefixo S3 |
| :--- | :--- | :--- |
| `_liquidez.json` | **Nuclea** | `bronze/input/bureaus/nuclea/cnpj/json` |
| `_quod.json` | **Quod** | `bronze/input/bureaus/quod/cnpj/json` |
| `_proscore.json` | **Proscore** | `bronze/input/bureaus/proscore/cnpj/json` |
| `_basic_data.json` | **BigDataCorp** | `bronze/input/bureaus/bigdatacorp/cnpj/json` |
| `_registration_data.json` | **BigDataCorp** | `bronze/input/bureaus/bigdatacorp/cnpj/json` |
| `_history_basic_data.json` | **BigDataCorp** | `bronze/input/bureaus/bigdatacorp/cnpj/json` |
| `_economic_group_relationships.json` | **BigDataCorp** | `bronze/input/bureaus/bigdatacorp/cnpj/json` |

---

## Ambientes S3

Os uploads utilizam profiles da AWS previamente configurados na máquina local (`~/.aws/credentials` ou `~/.aws/config`):

| Ambiente | Bucket | AWS Profile |
| :---: | :--- | :--- |
| `dev` | `dev-bevoc-datalake` | `grafeno-dev` |
| `stg` | `stg-bevoc-datalake` | `grafeno-stg` |
| `prd` | `prd-bevoc-datalake` | `grafeno-prd` |

---

## Pré-requisitos

- Python 3.10+ (definido em `.python-version`)
- AWS CLI configurado com os profiles acima (caso vá utilizar o envio para o S3)

---

## Instalação

1. Clone o repositório e acesse o diretório:
   ```bash
   git clone https://github.com/HelioCarvalhoGrafeno/rating_mock.git
   cd rating_mock
   ```

2. Crie e ative o ambiente virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

---

## Como Usar

### Argumentos da CLI

```text
usage: generate_mock.py [-h] [--env {dev,prd,stg}] [--no-local] [--dry-run] cnpj

positional arguments:
  cnpj                 CNPJ de destino (com ou sem mascara), 14 caracteres alfanumericos.

options:
  -h, --help           show this help message and exit
  --env {dev,prd,stg}  Ambiente de destino para upload no S3 (dev, stg ou prd).
                       Se omitido, apenas gera os arquivos localmente.
  --no-local           Nao escrever copia local em output/<cnpj>/ (apenas enviar ao S3).
  --dry-run            Mostra o que seria feito, sem enviar nada ao S3.
```

### 1. Gerar mocks apenas localmente

Cria os arquivos em `output/<CNPJ>/`:

```bash
# CNPJ alfanumérico com máscara
python generate_mock.py 12.ABC.345/0001-95

# CNPJ alfanumérico sem máscara (minúsculo é normalizado para maiúsculo)
python generate_mock.py 12abc345000195

# CNPJ numérico tradicional
python generate_mock.py 00.009.838/0001-46
```

### 2. Simular upload no S3 (`--dry-run`)

Mostra quais arquivos e chaves S3 seriam enviados, sem efetivamente publicar nada no bucket:

```bash
python generate_mock.py 12.ABC.345/0001-95 --env dev --dry-run
```

### 3. Gerar e publicar no S3

Gera a cópia local em `output/<CNPJ>/` e realiza o upload para o S3 com o profile AWS do ambiente correspondente:

```bash
# Upload para o ambiente de dev
python generate_mock.py 12.ABC.345/0001-95 --env dev

# Upload para o ambiente de homologação (stg)
python generate_mock.py 12.ABC.345/0001-95 --env stg
```

### 4. Publicar no S3 sem manter cópia local

Usa a flag `--no-local` para enviar os mocks direto ao S3 sem criar a pasta local:

```bash
python generate_mock.py 12.ABC.345/0001-95 --env dev --no-local
```

---

## Suporte a CNPJ Alfanumérico

A normalização de CNPJ (`normalize_cnpj`) trata as seguintes situações:
- Aceita formatos com pontuação (`XX.XXX.XXX/XXXX-XX`) e sem pontuação (`XXXXXXXXXXXXXX`).
- Aceita caracteres alfanuméricos (`0-9`, `A-Z`), normalizando minúsculas para maiúsculas.
- Valida o tamanho final de exatamente 14 caracteres, garantindo aderência ao padrão da Receita Federal.

---

## Estrutura do Projeto

```text
rating_mock/
├── generate_mock.py          # Script principal de geração e upload
├── requirements.txt          # Dependências Python (boto3)
├── .python-version           # Versão de referência do Python
├── .gitignore                # Arquivos ignorados pelo Git
├── README.md                 # Documentação do projeto
├── json/                     # Arquivos JSON de referência (CNPJ 00009838000146)
│   ├── 00009838000146_basic_data.json
│   ├── 00009838000146_economic_group_relationships.json
│   ├── 00009838000146_history_basic_data.json
│   ├── 00009838000146_liquidez.json
│   ├── 00009838000146_proscore.json
│   ├── 00009838000146_quod.json
│   └── 00009838000146_registration_data.json
└── output/                   # Diretório de saída dos mocks gerados
```
