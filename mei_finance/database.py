import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path


ACCOUNT_TYPES = {
    "Conta corrente": "bank",
    "Poupanca": "bank",
    "Dinheiro": "cash",
    "Cartao de credito": "credit",
}

DEFAULT_CATEGORIES = {
    "income": ["Vendas", "Servicos", "Outros recebimentos"],
    "expense": ["Aluguel", "Insumos", "Transporte", "Internet", "Taxas", "Equipamentos", "Outras despesas"],
    "transfer": ["Transferencia entre contas", "Pagamento de fatura", "Retirada"],
}


class FinanceStore:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
        self._seed_accounts()
        self._seed_categories()

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _create_tables(self):
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    account_type TEXT NOT NULL,
                    opening_balance_cents INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_date TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('income', 'expense', 'transfer')),
                    account_id INTEGER NOT NULL REFERENCES accounts(id),
                    destination_account_id INTEGER REFERENCES accounts(id),
                    category TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                    CHECK (
                        (kind = 'transfer' AND destination_account_id IS NOT NULL
                            AND destination_account_id != account_id)
                        OR (kind != 'transfer' AND destination_account_id IS NULL)
                    )
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('income', 'expense', 'transfer')),
                    UNIQUE (kind, name)
                );
                """
            )

    def _seed_accounts(self):
        with self._connection() as connection:
            account_count = connection.execute(
                "SELECT COUNT(*) FROM accounts"
            ).fetchone()[0]
            if account_count == 0:
                connection.executemany(
                    "INSERT INTO accounts (name, account_type) VALUES (?, ?)",
                    [
                        ("Banco principal", "bank"),
                        ("Dinheiro em caixa", "cash"),
                        ("Cartao da empresa", "credit"),
                    ],
                )

    def _seed_categories(self):
        with self._connection() as connection:
            category_count = connection.execute(
                "SELECT COUNT(*) FROM categories"
            ).fetchone()[0]
            if category_count == 0:
                connection.executemany(
                    "INSERT OR IGNORE INTO categories (name, kind) VALUES (?, ?)",
                    [
                        (name, kind)
                        for kind, names in DEFAULT_CATEGORIES.items()
                        for name in names
                    ],
                )
            legacy_categories = connection.execute(
                "SELECT DISTINCT category, kind FROM transactions"
            ).fetchall()
            connection.executemany(
                "INSERT OR IGNORE INTO categories (name, kind) VALUES (?, ?)",
                [(row["category"], row["kind"]) for row in legacy_categories],
            )

    def list_categories(self, kind=None):
        with self._connection() as connection:
            if kind:
                rows = connection.execute(
                    "SELECT * FROM categories WHERE kind = ? ORDER BY name", (kind,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM categories ORDER BY kind, name"
                ).fetchall()
        return [dict(row) for row in rows]

    def get_category(self, category_id):
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM categories WHERE id = ?", (category_id,)
            ).fetchone()
        return dict(row) if row else None

    def create_category(self, name, kind):
        clean_name = name.strip()
        self._validate_category(clean_name, kind)
        try:
            with self._connection() as connection:
                connection.execute(
                    "INSERT INTO categories (name, kind) VALUES (?, ?)",
                    (clean_name, kind),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("Ja existe uma categoria com esse nome para este tipo.") from error

    def update_category(self, category_id, name):
        clean_name = name.strip()
        category = self.get_category(category_id)
        if category is None:
            raise ValueError("Categoria nao encontrada.")
        self._validate_category(clean_name, category["kind"])
        try:
            with self._connection() as connection:
                connection.execute(
                    "UPDATE categories SET name = ? WHERE id = ?",
                    (clean_name, category_id),
                )
                connection.execute(
                    "UPDATE transactions SET category = ? WHERE category = ? AND kind = ?",
                    (clean_name, category["name"], category["kind"]),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("Ja existe uma categoria com esse nome para este tipo.") from error

    def delete_category(self, category_id):
        category = self.get_category(category_id)
        if category is None:
            return
        with self._connection() as connection:
            usage = connection.execute(
                "SELECT COUNT(*) FROM transactions WHERE category = ? AND kind = ?",
                (category["name"], category["kind"]),
            ).fetchone()[0]
            if usage:
                raise ValueError(
                    "Esta categoria esta em uso. Altere ou exclua os lancamentos associados antes."
                )
            connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    @staticmethod
    def _validate_category(name, kind):
        if not name:
            raise ValueError("Informe o nome da categoria.")
        if kind not in DEFAULT_CATEGORIES:
            raise ValueError("Selecione um tipo de categoria valido.")

    def list_accounts(self):
        with self._connection() as connection:
            accounts = connection.execute(
                "SELECT * FROM accounts ORDER BY name"
            ).fetchall()
            transactions = connection.execute(
                "SELECT kind, account_id, destination_account_id, amount_cents "
                "FROM transactions"
            ).fetchall()

        balances = {account["id"]: account["opening_balance_cents"] for account in accounts}
        types = {account["id"]: account["account_type"] for account in accounts}
        for transaction in transactions:
            amount = transaction["amount_cents"]
            source_id = transaction["account_id"]
            kind = transaction["kind"]
            if kind == "income":
                balances[source_id] += amount if types[source_id] != "credit" else -amount
            elif kind == "expense":
                balances[source_id] += -amount if types[source_id] != "credit" else amount
            else:
                balances[source_id] += -amount if types[source_id] != "credit" else amount
                destination_id = transaction["destination_account_id"]
                balances[destination_id] += (
                    amount if types[destination_id] != "credit" else -amount
                )

        return [
            {
                **dict(account),
                "balance_cents": balances[account["id"]],
                "type_label": self._type_label(account["account_type"]),
            }
            for account in accounts
        ]

    def create_account(self, name, account_type, opening_balance_cents=0):
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Informe o nome da conta.")
        if account_type not in {"bank", "cash", "credit"}:
            raise ValueError("Selecione um tipo de conta valido.")
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO accounts (name, account_type, opening_balance_cents) "
                "VALUES (?, ?, ?)",
                (clean_name, account_type, opening_balance_cents),
            )

    def get_account(self, account_id):
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_account(self, account_id, name, account_type, opening_balance_cents):
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Informe o nome da conta.")
        if account_type not in {"bank", "cash", "credit"}:
            raise ValueError("Selecione um tipo de conta valido.")
        with self._connection() as connection:
            connection.execute(
                """UPDATE accounts
                SET name = ?, account_type = ?, opening_balance_cents = ?
                WHERE id = ?""",
                (clean_name, account_type, opening_balance_cents, account_id),
            )

    def delete_account(self, account_id):
        with self._connection() as connection:
            usage = connection.execute(
                """SELECT COUNT(*) FROM transactions
                WHERE account_id = ? OR destination_account_id = ?""",
                (account_id, account_id),
            ).fetchone()[0]
            if usage:
                raise ValueError(
                    "Esta conta possui lancamentos. Exclua-os antes de excluir a conta."
                )
            connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    def add_transaction(
        self,
        transaction_date,
        kind,
        account_id,
        category,
        description,
        amount_cents,
        destination_account_id=None,
    ):
        self._validate_transaction(
            transaction_date, kind, account_id, category, amount_cents, destination_account_id
        )
        if kind != "transfer":
            destination_account_id = None

        with self._connection() as connection:
            connection.execute(
                """INSERT INTO transactions (
                    transaction_date, kind, account_id, destination_account_id,
                    category, description, amount_cents
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    transaction_date,
                    kind,
                    account_id,
                    destination_account_id,
                    category.strip(),
                    description.strip(),
                    amount_cents,
                ),
            )

    def get_transaction(self, transaction_id):
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_transaction(
        self,
        transaction_id,
        transaction_date,
        kind,
        account_id,
        category,
        description,
        amount_cents,
        destination_account_id=None,
    ):
        self._validate_transaction(
            transaction_date, kind, account_id, category, amount_cents, destination_account_id
        )
        if kind != "transfer":
            destination_account_id = None
        with self._connection() as connection:
            connection.execute(
                """UPDATE transactions SET
                    transaction_date = ?, kind = ?, account_id = ?,
                    destination_account_id = ?, category = ?, description = ?, amount_cents = ?
                WHERE id = ?""",
                (
                    transaction_date,
                    kind,
                    account_id,
                    destination_account_id,
                    category.strip(),
                    description.strip(),
                    amount_cents,
                    transaction_id,
                ),
            )

    def delete_transaction(self, transaction_id):
        with self._connection() as connection:
            connection.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))

    def _validate_transaction(
        self, transaction_date, kind, account_id, category, amount_cents, destination_account_id
    ):
        try:
            date.fromisoformat(transaction_date)
        except ValueError as error:
            raise ValueError("Informe uma data valida no formato AAAA-MM-DD.") from error
        if kind not in {"income", "expense", "transfer"}:
            raise ValueError("Selecione um tipo de lancamento valido.")
        if amount_cents <= 0:
            raise ValueError("O valor precisa ser maior que zero.")
        if not category.strip():
            raise ValueError("Selecione uma categoria.")
        if category.strip() not in {
            item["name"] for item in self.list_categories(kind)
        }:
            raise ValueError("Selecione uma categoria cadastrada para este tipo.")
        if kind == "transfer" and (
            destination_account_id is None or destination_account_id == account_id
        ):
            raise ValueError("A transferencia precisa ter duas contas diferentes.")

    def list_transactions(self, limit=200):
        with self._connection() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    """SELECT t.*, a.name AS account_name, d.name AS destination_name
                    FROM transactions t
                    JOIN accounts a ON a.id = t.account_id
                    LEFT JOIN accounts d ON d.id = t.destination_account_id
                    ORDER BY t.transaction_date DESC, t.id DESC
                    LIMIT ?""",
                    (limit,),
                ).fetchall()
            ]

    def monthly_totals(self, year_month=None):
        month = year_month or date.today().strftime("%Y-%m")
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT kind, COALESCE(SUM(amount_cents), 0) AS total
                FROM transactions
                WHERE transaction_date LIKE ? AND kind IN ('income', 'expense')
                GROUP BY kind""",
                (f"{month}-%",),
            ).fetchall()
        totals = {"income": 0, "expense": 0}
        for row in rows:
            totals[row["kind"]] = row["total"]
        return totals

    @staticmethod
    def _type_label(account_type):
        return {"bank": "Conta", "cash": "Dinheiro", "credit": "Credito"}[account_type]