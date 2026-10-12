from pathlib import Path

from mei_finance.ui import FinanceApp


def main():
    database_path = Path(__file__).parent / "data" / "mei_finance.db"
    app = FinanceApp(database_path)
    app.mainloop()


if __name__ == "__main__":
    main()