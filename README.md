# Invoices

Gerador de invoices em PDF com:

- dados em JSON;
- template em HTML;
- renderização em PDF com Playwright;
- sequência automática controlada por arquivo local;
- comandos curtos via `make`.

## Estrutura

- `generate_invoice.py`: gera o PDF final.
- `invoice-template.html`: template visual da invoice.
- `invoice-data.example.json`: exemplo público de dados.
- `sequence.txt.example`: exemplo do arquivo de sequência local.
- `Makefile`: atalhos de uso.
- `examples/`: exemplos públicos e anonimizados.
- `output/`: saída local das invoices geradas. Não sobe para o Git.

## Instalação

### Opção recomendada

```bash
make setup
```

Isso cria `.venv`, instala as dependências Python e baixa o Chromium do Playwright.

### Opção manual

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

## Comandos

Gerar invoice:

```bash
make invoice DATA=invoice-ford.json
```

Atalho por cliente:

```bash
make ford
```

Isso procura automaticamente por `invoice-ford.json`.
Se no futuro existir `invoice-spectrum.json`, você poderá usar:

```bash
make spectrum
```

Dry-run por cliente:

```bash
make ford-dry-run
```

E no futuro:

```bash
make spectrum-dry-run
```

Dry-run:

```bash
make dry-run DATA=invoice-ford.json
```

Gerar PDF e manter também o HTML renderizado:

```bash
make debug DATA=invoice-ford.json
```

Validar o projeto:

```bash
make check
```

Rodar apenas os testes:

```bash
make test
```

Instalar ou atualizar apenas o browser do Playwright:

```bash
make install-browser
```

## Fluxo de uso

1. Copie `invoice-data.example.json` para um arquivo seu, por exemplo `invoice-ford.json`.
2. Preencha os dados da invoice.
3. Gere o PDF com `make invoice DATA=invoice-ford.json`.
4. O arquivo final será salvo em `output/`.

## Sequência

O projeto usa um arquivo local `sequence.txt` para controlar o último número emitido.

- `sequence.txt` é local e ignorado pelo Git.
- `sequence.txt.example` é apenas referência.
- Se `sequence.txt` não existir, o gerador usa o maior número já encontrado em `output/`.
- Depois de uma geração bem-sucedida, o `sequence.txt` é atualizado.

## Formato dos dados

Campos principais do JSON:

- `seller_name`
- `seller_legal_name`
- `seller_tax_id`
- `seller_address_line1`
- `seller_address_line2`
- `seller_email`
- `client_name`
- `client_department`
- `client_address_line1`
- `client_address_line2`
- `client_email`
- `issue_date`
- `due_date`
- `currency`
- `notes`
- `items`

Cada item em `items` deve conter:

- `description`
- `quantity`
- `unit_price`

## Validação

O gerador valida o JSON antes de renderizar.

Erros cobertos:

- arquivo inexistente;
- JSON inválido;
- campos obrigatórios ausentes;
- `items` vazio ou malformado;
- quantidade menor ou igual a zero;
- preço unitário negativo;
- valores numéricos inválidos.

## Arquivos públicos e privados

Versionados no Git:

- código;
- template;
- exemplos públicos em `examples/`.

Ignorados pelo Git:

- invoices reais em `output/`;
- arquivos pessoais `invoice-*.json`;
- `.venv/`;
- `sequence.txt`.

## Exemplos

- `examples/invoice-example.json`
- `examples/invoice-example.html`

## Observações

- O layout final do PDF vem do template HTML.
- A geração de PDF usa Playwright + Chromium, o que mantém o projeto cross-platform.
- Para semanas fechadas, a descrição mais clara costuma ser algo como: `Services provided from Monday to Friday, 8 hours per day, totaling 40 hours.`
