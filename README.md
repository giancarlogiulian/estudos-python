# Fluxo MEI

Aplicativo desktop didatico para controle financeiro de uma empresa MEI. Foi construido com Python, Tkinter e SQLite, sem dependencias externas.

**Autoria da implementacao:** GitHub Copilot

**Supervisao do projeto:** usuario

## Executar

Requer Python 3.10 ou mais recente com Tkinter habilitado. No Windows, abra o terminal nesta pasta e execute:

```powershell
python main.py
```

O banco `data/mei_finance.db` e as contas iniciais de exemplo sao criados automaticamente na primeira execucao. Categorias usadas por lancamentos anteriores tambem sao importadas para o cadastro.

## Funcionalidades

- Registre receitas, despesas e transferencias entre contas, com data, categoria, descricao e valor.
- Cadastre contas correntes, poupanca, dinheiro em caixa e cartoes de credito, incluindo o saldo inicial.
- Mantenha categorias separadas para receitas, despesas e transferencias. Ao criar um lancamento, selecione uma categoria cadastrada para o tipo escolhido.
- Consulte receitas e despesas do mes, saldo disponivel e saldos individuais das contas.
- Edite ou exclua contas, categorias e lancamentos com duplo clique. A exclusao pede confirmacao; contas com lancamentos e categorias em uso nao podem ser excluidas.
- Renomear uma categoria atualiza tambem os lancamentos associados.

## Regras financeiras

- Compras feitas no cartao aumentam a fatura em aberto; pagamentos registrados como transferencia reduzem a fatura e o saldo da conta de origem.
- Transferencias movimentam os saldos das contas, mas nao sao somadas como receita ou despesa nos totais do mes.
- O saldo disponivel soma contas que nao sao cartoes. O saldo de um cartao representa a divida em aberto.
- Os valores sao armazenados em centavos para evitar erros comuns de arredondamento.

## Estrutura

- `main.py`: inicia a janela e define onde o banco de dados sera salvo.
- `mei_finance/database.py`: cria e acessa as tabelas SQLite, migra categorias existentes e aplica as regras de validacao e saldo.
- `mei_finance/ui.py`: implementa as abas, tabelas, formularios e interacoes Tkinter.
- `tests/test_database.py`: testa saldos, transferencias, categorias e operacoes de edicao e exclusao.

## Testes

Execute a suite automatizada com:

```powershell
python -m unittest discover -s tests -v
```