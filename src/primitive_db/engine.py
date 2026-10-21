"""Application startup, main loop and user command dispatch."""

import prompt
from prettytable import PrettyTable

from primitive_db import core, parser
from primitive_db.constants import COMMAND_PROMPT, EXIT_COMMAND, ID_COLUMN, META_FILE
from primitive_db.decorators import handle_db_errors
from primitive_db.utils import (
    delete_table_data,
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)


def print_help() -> None:
    """Print help for all commands."""

    print("\n***Операции с данными***")
    print("\nФункции:")
    print(
        "<command> insert into <имя_таблицы> values "
        "(<значение1>, <значение2>, ...) - создать запись."
    )
    print(
        "<command> select from <имя_таблицы> where <столбец> = <значение> "
        "- прочитать записи по условию."
    )
    print("<command> select from <имя_таблицы> - прочитать все записи.")
    print(
        "<command> update <имя_таблицы> set <столбец1> = <новое_значение1> "
        "where <столбец_условия> = <значение_условия> - обновить запись."
    )
    print(
        "<command> delete from <имя_таблицы> where <столбец> = <значение> "
        "- удалить запись."
    )
    print("<command> info <имя_таблицы> - вывести информацию о таблице.")

    print("\n***Процесс работы с таблицей***")
    print("Функции:")
    print("<command> create_table <имя_таблицы> <столбец1:тип> .. - создать таблицу")
    print("<command> list_tables - показать список всех таблиц")
    print("<command> drop_table <имя_таблицы> - удалить таблицу")

    print("\nОбщие команды:")
    print("<command> exit - выход из программы")
    print("<command> help - справочная информация\n")


def print_records(schema: dict[str, str], records: list[dict]) -> None:
    """Print table records using PrettyTable.

    Args:
        schema: Table schema {column: type}.
        records: Records to print.
    """
    if not records:
        print("Записи не найдены.")
        return
    table = PrettyTable()
    table.field_names = list(schema)
    for record in records:
        table.add_row([record.get(column) for column in schema])
    print(table)


def handle_list_tables(metadata: dict) -> None:
    """Print the list of database tables.

    Args:
        metadata: Current database metadata.
    """
    tables = core.list_tables(metadata)
    if not tables:
        print("Таблиц пока нет.")
    for table_name in tables:
        print(f"- {table_name}")


def handle_create_table(metadata: dict, params: list[str]) -> None:
    """Run the create_table command and save the metadata.

    Args:
        metadata: Current database metadata.
        params: Table name and column definitions.
    """
    table_name, *columns = params
    new_metadata = core.create_table(metadata, table_name, columns)
    if new_metadata is not None:
        save_metadata(META_FILE, new_metadata)


def handle_drop_table(metadata: dict, table_name: str) -> None:
    """Run the drop_table command and delete the table data.

    Args:
        metadata: Current database metadata.
        table_name: Name of the table to drop.
    """
    if not core.table_exists(metadata, table_name):
        return
    new_metadata = core.drop_table(metadata, table_name)
    if new_metadata is not None:
        save_metadata(META_FILE, new_metadata)
        delete_table_data(table_name)


def handle_info(metadata: dict, table_name: str) -> None:
    """Print the table schema and record count.

    Args:
        metadata: Current database metadata.
        table_name: Table name.
    """
    if not core.table_exists(metadata, table_name):
        return
    print(f"Таблица: {table_name}")
    print(f"Столбцы: {core.format_columns(metadata[table_name])}")
    print(f"Количество записей: {len(load_table_data(table_name))}")


def handle_insert(metadata: dict, user_input: str) -> None:
    """Run the insert command and save the table data.

    Args:
        metadata: Current database metadata.
        user_input: Entered command.
    """
    table_name, values = parser.parse_insert_command(user_input)
    table_data = core.insert(metadata, table_name, values)
    if table_data is not None:
        save_table_data(table_name, table_data)


def handle_select(metadata: dict, user_input: str) -> None:
    """Run the select command and print the result as a table.

    Args:
        metadata: Current database metadata.
        user_input: Entered command.
    """
    table_name, where_clause = parser.parse_select_command(user_input)
    if not core.table_exists(metadata, table_name):
        return
    if where_clause and not core.validate_clause(metadata, table_name, where_clause):
        return
    records = core.select(load_table_data(table_name), where_clause)
    if records is not None:
        print_records(metadata[table_name], records)


def get_matching_ids(table_data: list[dict], where_clause: dict) -> list[int]:
    """Return the IDs of records that satisfy the condition.

    Args:
        table_data: Table records.
        where_clause: Condition {column: value}.

    Returns:
        List of IDs of matching records.
    """
    matching = core.find_matching(table_data, where_clause)
    return [record[ID_COLUMN] for record in matching]


def handle_update(metadata: dict, user_input: str) -> None:
    """Run the update command and save the table data.

    Args:
        metadata: Current database metadata.
        user_input: Entered command.
    """
    table_name, set_clause, where_clause = parser.parse_update_command(user_input)
    if not core.table_exists(metadata, table_name):
        return
    if not core.validate_clause(metadata, table_name, set_clause):
        return
    if not core.validate_clause(metadata, table_name, where_clause):
        return
    table_data = load_table_data(table_name)
    record_ids = get_matching_ids(table_data, where_clause)
    if not record_ids:
        print("Записи, удовлетворяющие условию, не найдены.")
        return
    table_data = core.update(table_data, set_clause, where_clause)
    if table_data is None:
        return
    save_table_data(table_name, table_data)
    for record_id in record_ids:
        print(f'Запись с ID={record_id} в таблице "{table_name}" успешно обновлена.')


def handle_delete(metadata: dict, user_input: str) -> None:
    """Run the delete command and save the table data.

    Args:
        metadata: Current database metadata.
        user_input: Entered command.
    """
    table_name, where_clause = parser.parse_delete_command(user_input)
    if not core.table_exists(metadata, table_name):
        return
    if not core.validate_clause(metadata, table_name, where_clause):
        return
    table_data = load_table_data(table_name)
    record_ids = get_matching_ids(table_data, where_clause)
    if not record_ids:
        print("Записи, удовлетворяющие условию, не найдены.")
        return
    table_data = core.delete(table_data, where_clause)
    if table_data is None:
        return
    save_table_data(table_name, table_data)
    for record_id in record_ids:
        print(f'Запись с ID={record_id} успешно удалена из таблицы "{table_name}".')


@handle_db_errors
def execute_command(metadata: dict, user_input: str) -> None:
    """Parse and execute a single user command.

    Args:
        metadata: Current database metadata.
        user_input: Entered command.
    """
    args = parser.split_arguments(user_input)
    if not args:
        return
    command, *params = args
    match command:
        case "help" if not params:
            print_help()
        case "list_tables" if not params:
            handle_list_tables(metadata)
        case "create_table" if len(params) >= 2:
            handle_create_table(metadata, params)
        case "drop_table" if len(params) == 1:
            handle_drop_table(metadata, params[0])
        case "info" if len(params) == 1:
            handle_info(metadata, params[0])
        case "insert":
            handle_insert(metadata, user_input)
        case "select":
            handle_select(metadata, user_input)
        case "update":
            handle_update(metadata, user_input)
        case "delete":
            handle_delete(metadata, user_input)
        case "exit" | "help" | "list_tables" | "create_table" | "drop_table" | "info":
            raise core.invalid_value_error(user_input)
        case _:
            print(f"Функции {command} нет. Попробуйте снова.")


def run() -> None:
    """Run the main database loop."""
    print_help()
    while True:
        metadata = load_metadata(META_FILE)
        try:
            user_input = prompt.string(COMMAND_PROMPT)
        except (EOFError, KeyboardInterrupt):
            # Input closed (Ctrl+D / Ctrl+C): exit without a traceback.
            print()
            break
        if user_input.strip() == EXIT_COMMAND:
            break
        execute_command(metadata, user_input)
