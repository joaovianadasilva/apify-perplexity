# Apify Perplexity Bridge

Actor do Apify escrito em Python que recebe prompts, chama a API do Perplexity e persiste a resposta estruturada no dataset padrão.

## Estrutura do projeto

```
.
├── .actor/actor.json        # Metadados do Actor (nome, schema de input, variáveis)
├── Dockerfile               # Imagem baseada em apify/actor-python com dependências
├── INPUT_SCHEMA.json        # Esquema utilizado pela UI do Apify para montar o formulário de input
├── README.md                # Instruções de uso
├── requirements.txt         # Dependências Python (apify SDK + cliente Perplexity)
└── src/
    └── main.py              # Implementação principal do Actor
```

## Pré-requisitos

* [Apify CLI](https://docs.apify.com/cli) instalado localmente.
* Conta no [Perplexity](https://www.perplexity.ai/) com uma chave de API ativa (`PERPLEXITY_API_KEY`).

## Como executar localmente

1. Instale as dependências Python (opcional em execução local fora do runtime Apify):

   ```bash
   pip install -r requirements.txt
   ```

2. Defina a variável `PERPLEXITY_API_KEY` no ambiente.

3. Rode o Actor com a CLI do Apify:

   ```bash
   apify run --purge
   ```

   O input pode ser ajustado editando `apify_storage/key_value_stores/default/INPUT.json` ou passando `--input '{"prompt": "Pergunta"}'`.

## Parâmetros de entrada

O Actor aceita os seguintes campos (ver `INPUT_SCHEMA.json` para detalhes):

| Campo         | Tipo      | Descrição |
|---------------|-----------|-----------|
| `prompt`      | string    | Pergunta enviada ao modelo. Ignorado se `messages` for informado. |
| `systemPrompt`| string    | Mensagem de sistema opcional que antecede as demais mensagens. |
| `messages`    | array     | Lista completa de mensagens para a API do Perplexity. |
| `model`       | string    | ID do modelo Perplexity. Default `llama-3.1-sonar-small-128k-online`. |
| `temperature` | number    | Controle de criatividade. Default `0.2`. |
| `topP`        | number    | Top-p sampling. Default `0.95`. |
| `maxTokens`   | integer   | Limite máximo de tokens de saída. |
| `searchMode`  | string    | Ajusta o modo de busca híbrida (`auto`, `online`, etc.). |
| `returnRaw`   | boolean   | Quando `true`, salva a resposta completa no Key-value store padrão. |

## Saída

Cada execução grava uma entrada no dataset padrão com:

* `prompt` – resumo do prompt enviado.
* `messages` – mensagens enviadas ao Perplexity.
* `model` – modelo utilizado.
* `response` – conteúdo textual retornado.
* `citations` – citações fornecidas pelo Perplexity (quando disponíveis).
* `usage` – métricas de tokens consumidos.

Quando `returnRaw` é verdadeiro, a resposta integral também é salva com a chave `PERPLEXITY_COMPLETION` no Key-value store padrão da execução.

## Deploy no Apify

1. Faça login na CLI: `apify login`.
2. Publique o Actor para o cloud: `apify push`.
3. No Apify Console, configure a variável secreta `PERPLEXITY_API_KEY` e execute o Actor via UI, schedule ou chamadas `apify call`.

## Licença

MIT.
