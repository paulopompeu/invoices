# Invoice Template

Os PDFs existentes servem como referência visual, mas não são a melhor base para gerar novas invoices com consistência.

A forma mais segura de padronizar é:

1. Manter um template único.
2. Preencher apenas os dados variáveis de cada invoice.
3. Gerar o arquivo final com uma sequência numérica controlada.

## Arquivos

- `invoice-template.html`: template visual padronizado.
- `invoice-data.example.json`: exemplo de dados de entrada.
- `generate_invoice.py`: gera uma invoice nova em PDF.
- `Makefile`: atalhos para setup e geração das invoices.
- `examples/`: exemplos publicos e anonimizados que podem ficar no repositório.

Os enderecos agora sao separados em duas linhas:

- `seller_address_line1` e `client_address_line1`: numero e rua
- `seller_address_line2` e `client_address_line2`: cidade, estado e zip code

## Fluxo recomendado

## Instalacao

Via `make`:

```bash
make setup
```

Ou manualmente:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

1. Copie `invoice-data.example.json` para um novo arquivo, por exemplo `invoice-04.json`.
2. Edite apenas os campos do JSON.
3. Gere a invoice:

Com `make`:

```bash
make invoice DATA=invoice-04.json
```

Ou manualmente:

```bash
.venv/bin/python generate_invoice.py --data invoice-04.json
```

4. O script detecta o próximo número com base nos arquivos do diretório.
5. O PDF final será salvo em `output/invoice-0004.pdf`.

## Padrao de nomes

Todas as invoices finais ficam em `output/` com este formato:

- `invoice-0001.pdf`
- `invoice-0002.pdf`
- `invoice-0003.pdf`

O sequencial automatico passa a considerar apenas os arquivos dentro de `output/`.

Arquivos em `output/` sao gerados localmente e nao devem ser versionados.
Se voce quiser manter uma invoice publica de exemplo no repositório, use a pasta `examples/`.

Se quiser forçar um número específico:

```bash
.venv/bin/python generate_invoice.py --data invoice-04.json --number 4
```

Para testar sem gerar arquivo:

```bash
make dry-run DATA=invoice-04.json
```

ou:

```bash
.venv/bin/python generate_invoice.py --data invoice-04.json --dry-run
```

Para manter tambem o HTML renderizado para debug:

```bash
make debug DATA=invoice-04.json
```

ou:

```bash
.venv/bin/python generate_invoice.py --data invoice-04.json --keep-html
```

## Observações

- O número da invoice fica separado do nome do arquivo original, evitando confusão como `Invoice 1 (7)-1.pdf`.
- A estrutura visual, textos fixos e campos obrigatórios ficam centralizados em um único template.
- Para semanas fechadas, o ideal e mais claro e descrever o item com periodo + carga horaria total, por exemplo: `Services provided from Monday to Friday, 8 hours per day, totaling 40 hours.`
- A geracao de PDF usa Playwright + Chromium para manter o layout do HTML de forma cross-platform.
