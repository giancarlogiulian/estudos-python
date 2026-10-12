import tempfile
import unittest
from pathlib import Path

from mei_finance.database import FinanceStore


class FinanceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.store = FinanceStore(Path(self.temp_directory.name) / "test.db")
        self.accounts = {account["name"]: account for account in self.store.list_accounts()}

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_income_and_expense_update_bank_balance(self):
        bank_id = self.accounts["Banco principal"]["id"]
        self.store.add_transaction("2026-10-01", "income", bank_id, "Vendas", "", 12500)
        self.store.add_transaction("2026-10-02", "expense", bank_id, "Insumos", "", 4200)

        bank = next(account for account in self.store.list_accounts() if account["id"] == bank_id)
        self.assertEqual(bank["balance_cents"], 8300)

    def test_credit_expense_and_bank_payment_reduce_card_debt(self):
        bank_id = self.accounts["Banco principal"]["id"]
        card_id = self.accounts["Cartao da empresa"]["id"]
        self.store.add_transaction("2026-10-01", "expense", card_id, "Insumos", "", 8900)
        self.store.add_transaction(
            "2026-10-05", "transfer", bank_id, "Pagamento de fatura", "", 5000, card_id
        )

        balances = {account["id"]: account["balance_cents"] for account in self.store.list_accounts()}
        self.assertEqual(balances[bank_id], -5000)
        self.assertEqual(balances[card_id], 3900)

    def test_transfers_do_not_count_as_income_or_expense(self):
        bank_id = self.accounts["Banco principal"]["id"]
        cash_id = self.accounts["Dinheiro em caixa"]["id"]
        self.store.add_transaction(
            "2026-10-08", "transfer", bank_id, "Retirada", "", 2000, cash_id
        )

        self.assertEqual(self.store.monthly_totals("2026-10"), {"income": 0, "expense": 0})

    def test_transaction_can_be_edited_and_deleted(self):
        bank_id = self.accounts["Banco principal"]["id"]
        self.store.add_transaction("2026-10-10", "income", bank_id, "Vendas", "", 7000)
        transaction_id = self.store.list_transactions()[0]["id"]

        self.store.update_transaction(
            transaction_id, "2026-10-11", "expense", bank_id, "Aluguel", "Sala", 2500
        )
        edited = self.store.get_transaction(transaction_id)
        self.assertEqual(edited["category"], "Aluguel")
        self.assertEqual(self.store.monthly_totals("2026-10"), {"income": 0, "expense": 2500})

        self.store.delete_transaction(transaction_id)
        self.assertIsNone(self.store.get_transaction(transaction_id))
        self.assertEqual(self.store.monthly_totals("2026-10"), {"income": 0, "expense": 0})

    def test_account_can_be_edited_and_deleted_without_transactions(self):
        bank_id = self.accounts["Banco principal"]["id"]
        self.store.update_account(bank_id, "Conta operacional", "bank", 15000)

        edited = self.store.get_account(bank_id)
        self.assertEqual(edited["name"], "Conta operacional")
        self.assertEqual(edited["opening_balance_cents"], 15000)

        self.store.delete_account(bank_id)
        self.assertIsNone(self.store.get_account(bank_id))

    def test_account_with_transactions_cannot_be_deleted(self):
        bank_id = self.accounts["Banco principal"]["id"]
        self.store.add_transaction("2026-10-12", "income", bank_id, "Vendas", "", 1000)

        with self.assertRaisesRegex(ValueError, "possui lancamentos"):
            self.store.delete_account(bank_id)

    def test_transaction_category_must_match_registered_kind(self):
        bank_id = self.accounts["Banco principal"]["id"]

        with self.assertRaisesRegex(ValueError, "categoria cadastrada"):
            self.store.add_transaction("2026-10-12", "expense", bank_id, "Vendas", "", 1000)

    def test_category_rename_updates_history_and_in_use_category_cannot_be_deleted(self):
        bank_id = self.accounts["Banco principal"]["id"]
        self.store.create_category("Consultoria", "income")
        category = next(
            item for item in self.store.list_categories("income")
            if item["name"] == "Consultoria"
        )
        self.store.add_transaction("2026-10-12", "income", bank_id, "Consultoria", "", 5000)

        self.store.update_category(category["id"], "Atendimento")
        self.assertEqual(self.store.list_transactions()[0]["category"], "Atendimento")
        with self.assertRaisesRegex(ValueError, "esta em uso"):
            self.store.delete_category(category["id"])

        with self.assertRaisesRegex(ValueError, "Ja existe"):
            self.store.create_category("Vendas", "income")

    def test_existing_transaction_categories_are_imported(self):
        bank_id = self.accounts["Banco principal"]["id"]
        with self.store._connection() as connection:
            connection.execute(
                """INSERT INTO transactions (
                    transaction_date, kind, account_id, category, amount_cents
                ) VALUES (?, ?, ?, ?, ?)""",
                ("2026-10-12", "income", bank_id, "Servico legado", 1000),
            )

        reloaded_store = FinanceStore(self.store.database_path)
        legacy_names = {
            category["name"] for category in reloaded_store.list_categories("income")
        }
        self.assertIn("Servico legado", legacy_names)


if __name__ == "__main__":
    unittest.main()