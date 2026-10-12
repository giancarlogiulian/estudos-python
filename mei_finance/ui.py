import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from mei_finance.database import ACCOUNT_TYPES, FinanceStore


def format_money(cents):
    value = cents / 100
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def parse_money(value):
    normalized = value.strip().replace("R$", "").replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    return int(round(float(normalized) * 100))


class FinanceApp(tk.Tk):
    def __init__(self, database_path):
        super().__init__()
        self.store = FinanceStore(database_path)
        self.title("Fluxo MEI | Controle financeiro")
        self.geometry("1040x700")
        self.minsize(780, 560)
        self.configure(bg="#f3f5f2")
        self._configure_styles()
        self._build_layout()
        self.refresh()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f5f2")
        style.configure("TLabel", background="#f3f5f2", foreground="#26332d", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 21), foreground="#193b2b")
        style.configure("Muted.TLabel", foreground="#69756f")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#69756f", font=("Segoe UI", 9))
        style.configure("CardValue.TLabel", background="#ffffff", foreground="#193b2b", font=("Segoe UI Semibold", 18))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(14, 9), background="#216b45", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#195637")])
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7))
        style.configure("TNotebook", background="#f3f5f2", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 9), font=("Segoe UI Semibold", 10), background="#e7ebe7")
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#193b2b")])
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10), background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#e9eeea", foreground="#39473f", padding=8)
        style.map("Treeview", background=[("selected", "#dcebe1")], foreground=[("selected", "#193b2b")])

    def _build_layout(self):
        header = ttk.Frame(self, padding=(28, 22, 28, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Fluxo MEI", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Controle financeiro", style="Muted.TLabel").pack(side="left", padx=(12, 0), pady=(7, 0))
        ttk.Button(header, text="+  Lancamento", style="Primary.TButton", command=self.open_transaction_dialog).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=28, pady=(4, 24))
        self.overview_tab = ttk.Frame(self.notebook, padding=20)
        self.transactions_tab = ttk.Frame(self.notebook, padding=20)
        self.accounts_tab = ttk.Frame(self.notebook, padding=20)
        self.categories_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.overview_tab, text="Visao geral")
        self.notebook.add(self.transactions_tab, text="Lancamentos")
        self.notebook.add(self.accounts_tab, text="Contas")
        self.notebook.add(self.categories_tab, text="Categorias")
        self._build_overview()
        self._build_transactions()
        self._build_accounts()
        self._build_categories()

    def _build_overview(self):
        ttk.Label(self.overview_tab, text="Resumo do mes", style="Title.TLabel").pack(anchor="w", pady=(0, 16))
        cards = ttk.Frame(self.overview_tab)
        cards.pack(fill="x", pady=(0, 22))
        for index, (key, title) in enumerate(
            [("income", "Receitas no mes"), ("expense", "Despesas no mes"), ("available", "Saldo disponivel")]
        ):
            cards.columnconfigure(index, weight=1)
            card = ttk.Frame(cards, style="Card.TFrame", padding=(16, 14))
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 8, 0 if index == 2 else 8))
            ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
            value_label = ttk.Label(card, text="R$ 0,00", style="CardValue.TLabel")
            value_label.pack(anchor="w", pady=(8, 0))
            setattr(self, f"{key}_value", value_label)

        row = ttk.Frame(self.overview_tab)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Movimentacoes recentes", font=("Segoe UI Semibold", 12)).pack(side="left")
        ttk.Button(row, text="Ver todos", command=lambda: self.notebook.select(self.transactions_tab)).pack(side="right")
        self.recent_tree = self._make_transaction_tree(self.overview_tab, height=8)
        self.recent_tree.pack(fill="both", expand=True)
        self.recent_tree.bind("<Double-1>", self._on_transaction_double_click)

    def _build_transactions(self):
        top = ttk.Frame(self.transactions_tab)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Lancamentos", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="+  Novo lancamento", style="Primary.TButton", command=self.open_transaction_dialog).pack(side="right")
        self.transaction_tree = self._make_transaction_tree(self.transactions_tab)
        self.transaction_tree.pack(fill="both", expand=True)
        self.transaction_tree.bind("<Double-1>", self._on_transaction_double_click)

    def _make_transaction_tree(self, parent, height=14):
        columns = ("date", "kind", "category", "account", "amount")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=height)
        for key, title, width in [
            ("date", "Data", 105),
            ("kind", "Tipo", 100),
            ("category", "Categoria", 150),
            ("account", "Conta", 190),
            ("amount", "Valor", 130),
        ]:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="e" if key == "amount" else "w")
        tree.column("category", stretch=True)
        tree.column("account", stretch=True)
        tree.tag_configure("income", foreground="#216b45")
        tree.tag_configure("expense", foreground="#a44935")
        tree.tag_configure("transfer", foreground="#526b83")
        return tree

    def _build_accounts(self):
        top = ttk.Frame(self.accounts_tab)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Contas e saldos", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="+  Nova conta", style="Primary.TButton", command=self.open_account_dialog).pack(side="right")
        self.account_tree = ttk.Treeview(
            self.accounts_tab,
            columns=("name", "type", "balance"),
            show="headings",
            height=12,
        )
        for key, title, width in [("name", "Conta", 300), ("type", "Tipo", 180), ("balance", "Saldo / fatura", 180)]:
            self.account_tree.heading(key, text=title)
            self.account_tree.column(key, width=width, anchor="e" if key == "balance" else "w")
        self.account_tree.pack(fill="both", expand=True)
        self.account_tree.bind("<Double-1>", self._on_account_double_click)
        ttk.Label(
            self.accounts_tab,
            text="Cartoes mostram a fatura em aberto; pagamentos podem ser registrados como transferencia.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(12, 0))

    def _build_categories(self):
        top = ttk.Frame(self.categories_tab)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Categorias", style="Title.TLabel").pack(side="left")
        ttk.Button(
            top,
            text="+  Nova categoria",
            style="Primary.TButton",
            command=self.open_category_dialog,
        ).pack(side="right")
        self.category_tree = ttk.Treeview(
            self.categories_tab,
            columns=("name", "kind"),
            show="headings",
            height=14,
        )
        self.category_tree.heading("name", text="Categoria")
        self.category_tree.heading("kind", text="Tipo de lancamento")
        self.category_tree.column("name", width=300, anchor="w")
        self.category_tree.column("kind", width=220, anchor="w")
        self.category_tree.pack(fill="both", expand=True)
        self.category_tree.bind("<Double-1>", self._on_category_double_click)

    def refresh(self):
        accounts = self.store.list_accounts()
        totals = self.store.monthly_totals()
        available = sum(account["balance_cents"] for account in accounts if account["account_type"] != "credit")
        self.income_value.configure(text=format_money(totals["income"]))
        self.expense_value.configure(text=format_money(totals["expense"]))
        self.available_value.configure(text=format_money(available))
        self._refresh_transaction_tree(self.transaction_tree, accounts)
        self._refresh_transaction_tree(self.recent_tree, accounts, limit=8)
        for item in self.account_tree.get_children():
            self.account_tree.delete(item)
        for account in accounts:
            self.account_tree.insert(
                "",
                "end",
                iid=str(account["id"]),
                values=(account["name"], account["type_label"], format_money(account["balance_cents"])),
            )
        self._refresh_categories()

    def _refresh_categories(self):
        kind_labels = {
            "income": "Receita",
            "expense": "Despesa",
            "transfer": "Transferencia",
        }
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        for category in self.store.list_categories():
            self.category_tree.insert(
                "",
                "end",
                iid=str(category["id"]),
                values=(category["name"], kind_labels[category["kind"]]),
            )

    def _refresh_transaction_tree(self, tree, accounts, limit=200):
        account_names = {account["id"]: account["name"] for account in accounts}
        for item in tree.get_children():
            tree.delete(item)
        for transaction in self.store.list_transactions(limit):
            kind = transaction["kind"]
            label = {"income": "Receita", "expense": "Despesa", "transfer": "Transferencia"}[kind]
            account = account_names[transaction["account_id"]]
            if kind == "transfer":
                account = f"{account} -> {transaction['destination_name']}"
            tree.insert(
                "",
                "end",
                iid=str(transaction["id"]),
                values=(
                    transaction["transaction_date"],
                    label,
                    transaction["category"],
                    account,
                    format_money(transaction["amount_cents"]),
                ),
                tags=(kind,),
            )

    def open_transaction_dialog(self, transaction_id=None):
        transaction = self.store.get_transaction(transaction_id) if transaction_id else None
        if transaction_id and transaction is None:
            return
        accounts = self.store.list_accounts()
        if not accounts:
            messagebox.showerror("Sem contas", "Cadastre uma conta antes de criar lancamentos.", parent=self)
            return
        dialog = tk.Toplevel(self)
        dialog.title("Editar lancamento" if transaction else "Novo lancamento")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        title = "Editar lancamento" if transaction else "Novo lancamento"
        self._dialog_frame(dialog, title)
        form = ttk.Frame(dialog, padding=(24, 0, 24, 20))
        form.pack(fill="both")

        kinds = {"Receita": "income", "Despesa": "expense", "Transferencia": "transfer"}
        kind_labels = {value: label for label, value in kinds.items()}
        account_map = {account["name"]: account["id"] for account in accounts}
        account_names = {account["id"]: account["name"] for account in accounts}
        labels = list(account_map)
        kind_var = tk.StringVar(value=kind_labels[transaction["kind"]] if transaction else "Despesa")
        account_var = tk.StringVar(
            value=account_names[transaction["account_id"]] if transaction else labels[0]
        )
        default_destination = labels[1] if len(labels) > 1 else labels[0]
        destination_var = tk.StringVar(
            value=account_names[transaction["destination_account_id"]]
            if transaction and transaction["destination_account_id"]
            else default_destination
        )
        date_var = tk.StringVar(
            value=transaction["transaction_date"] if transaction else date.today().isoformat()
        )
        category_options = [
            item["name"] for item in self.store.list_categories(kinds[kind_var.get()])
        ]
        category_var = tk.StringVar(
            value=transaction["category"]
            if transaction
            else category_options[0] if category_options else ""
        )
        amount_var = tk.StringVar(
            value=format_money(transaction["amount_cents"]) if transaction else ""
        )
        description_var = tk.StringVar(value=transaction["description"] if transaction else "")
        destination_row = {}

        self._form_row(form, 0, "Tipo", ttk.Combobox, textvariable=kind_var, values=list(kinds), state="readonly")
        self._form_row(form, 1, "Data (AAAA-MM-DD)", ttk.Entry, textvariable=date_var)
        self._form_row(form, 2, "Conta", ttk.Combobox, textvariable=account_var, values=labels, state="readonly")
        self._form_row(
            form, 3, "Destino", ttk.Combobox, destination_row,
            textvariable=destination_var, values=labels, state="readonly"
        )
        category_combo = self._form_row(
            form,
            4,
            "Categoria",
            ttk.Combobox,
            textvariable=category_var,
            values=category_options,
            state="readonly",
        )
        self._form_row(form, 5, "Valor (R$)", ttk.Entry, textvariable=amount_var)
        self._form_row(form, 6, "Descricao", ttk.Entry, textvariable=description_var)
        self._set_row_visible(destination_row, False)

        def update_kind(*_):
            is_transfer = kinds[kind_var.get()] == "transfer"
            self._set_row_visible(destination_row, is_transfer)
            category_names = [
                item["name"] for item in self.store.list_categories(kinds[kind_var.get()])
            ]
            category_combo.configure(values=category_names)
            if category_var.get() not in category_names:
                category_var.set(category_names[0] if category_names else "")

        kind_var.trace_add("write", update_kind)

        def save():
            try:
                save_transaction = (
                    self.store.update_transaction if transaction else self.store.add_transaction
                )
                arguments = (
                    date_var.get().strip(),
                    kinds[kind_var.get()],
                    account_map[account_var.get()],
                    category_var.get(),
                    description_var.get(),
                    parse_money(amount_var.get()),
                    account_map[destination_var.get()] if kinds[kind_var.get()] == "transfer" else None,
                )
                if transaction:
                    save_transaction(transaction_id, *arguments)
                else:
                    save_transaction(*arguments)
            except (ValueError, KeyError) as error:
                messagebox.showerror("Lancamento invalido", str(error), parent=dialog)
                return
            except Exception as error:
                messagebox.showerror("Nao foi possivel salvar", str(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh()

        def delete():
            if not messagebox.askyesno(
                "Excluir lancamento", "Deseja excluir este lancamento?", parent=dialog
            ):
                return
            self.store.delete_transaction(transaction_id)
            dialog.destroy()
            self.refresh()

        self._dialog_buttons(dialog, save, delete if transaction else None)

    def _on_account_double_click(self, event):
        item_id = event.widget.identify_row(event.y)
        if item_id:
            self.open_account_dialog(int(item_id))

    def _on_transaction_double_click(self, event):
        item_id = event.widget.identify_row(event.y)
        if item_id:
            self.open_transaction_dialog(int(item_id))

    def _on_category_double_click(self, event):
        item_id = event.widget.identify_row(event.y)
        if item_id:
            self.open_category_dialog(int(item_id))

    def open_category_dialog(self, category_id=None):
        category = self.store.get_category(category_id) if category_id else None
        if category_id and category is None:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Editar categoria" if category else "Nova categoria")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._dialog_frame(dialog, "Editar categoria" if category else "Cadastrar categoria")
        form = ttk.Frame(dialog, padding=(24, 0, 24, 20))
        form.pack(fill="both")
        kind_labels = {
            "income": "Receita",
            "expense": "Despesa",
            "transfer": "Transferencia",
        }
        kind_values = {label: kind for kind, label in kind_labels.items()}
        name_var = tk.StringVar(value=category["name"] if category else "")
        kind_var = tk.StringVar(
            value=kind_labels[category["kind"]] if category else "Despesa"
        )
        self._form_row(form, 0, "Nome", ttk.Entry, textvariable=name_var)
        self._form_row(
            form,
            1,
            "Tipo de lancamento",
            ttk.Combobox,
            textvariable=kind_var,
            values=list(kind_values),
            state="disabled" if category else "readonly",
        )

        def save():
            try:
                if category:
                    self.store.update_category(category_id, name_var.get())
                else:
                    self.store.create_category(name_var.get(), kind_values[kind_var.get()])
            except ValueError as error:
                messagebox.showerror("Categoria invalida", str(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh()

        def delete():
            if not messagebox.askyesno(
                "Excluir categoria", "Deseja excluir esta categoria?", parent=dialog
            ):
                return
            try:
                self.store.delete_category(category_id)
            except ValueError as error:
                messagebox.showerror("Categoria nao excluida", str(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh()

        self._dialog_buttons(dialog, save, delete if category else None)

    def open_account_dialog(self, account_id=None):
        account = self.store.get_account(account_id) if account_id else None
        if account_id and account is None:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Editar conta" if account else "Nova conta")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._dialog_frame(dialog, "Editar conta" if account else "Cadastrar conta")
        form = ttk.Frame(dialog, padding=(24, 0, 24, 20))
        form.pack(fill="both")
        account_type_labels = {value: label for label, value in ACCOUNT_TYPES.items()}
        name_var = tk.StringVar(value=account["name"] if account else "")
        type_var = tk.StringVar(
            value=account_type_labels[account["account_type"]]
            if account
            else "Conta corrente"
        )
        balance_var = tk.StringVar(
            value=format_money(account["opening_balance_cents"]) if account else "0,00"
        )
        self._form_row(form, 0, "Nome", ttk.Entry, textvariable=name_var)
        self._form_row(
            form, 1, "Tipo", ttk.Combobox,
            textvariable=type_var, values=list(ACCOUNT_TYPES), state="readonly"
        )
        self._form_row(
            form, 2, "Saldo inicial / fatura (R$)", ttk.Entry, textvariable=balance_var
        )

        def save():
            try:
                save_account = self.store.update_account if account else self.store.create_account
                values = (
                    name_var.get(),
                    ACCOUNT_TYPES[type_var.get()],
                    parse_money(balance_var.get()),
                )
                if account:
                    save_account(account_id, *values)
                else:
                    save_account(*values)
            except ValueError as error:
                messagebox.showerror("Conta invalida", str(error), parent=dialog)
                return
            except Exception as error:
                messagebox.showerror("Nao foi possivel salvar", str(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh()

        def delete():
            if not messagebox.askyesno(
                "Excluir conta", "Deseja excluir esta conta?", parent=dialog
            ):
                return
            try:
                self.store.delete_account(account_id)
            except ValueError as error:
                messagebox.showerror("Conta nao excluida", str(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh()

        self._dialog_buttons(dialog, save, delete if account else None)

    @staticmethod
    def _dialog_frame(dialog, title):
        ttk.Label(dialog, text=title, style="Title.TLabel", padding=(24, 20, 24, 16)).pack(anchor="w")

    @staticmethod
    def _form_row(parent, row, label, widget_type, row_holder=None, **widget_options):
        holder = ttk.Frame(parent)
        holder.grid(row=row, column=0, sticky="ew", pady=5)
        holder.columnconfigure(1, weight=1)
        ttk.Label(holder, text=label, width=24).grid(row=0, column=0, sticky="w", padx=(0, 12))
        widget = widget_type(holder, **widget_options)
        widget.grid(row=0, column=1, sticky="ew")
        if row_holder is not None:
            row_holder["frame"] = holder
        return widget

    @staticmethod
    def _set_row_visible(row_holder, visible):
        frame = row_holder.get("frame")
        if frame is None:
            return
        if visible:
            frame.grid()
        else:
            frame.grid_remove()

    @staticmethod
    def _dialog_buttons(dialog, save_command, delete_command=None):
        buttons = ttk.Frame(dialog, padding=(24, 0, 24, 20))
        buttons.pack(fill="x")
        if delete_command:
            ttk.Button(buttons, text="Excluir", command=delete_command).pack(side="left")
        ttk.Button(buttons, text="Cancelar", command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Salvar", style="Primary.TButton", command=save_command).pack(side="right")