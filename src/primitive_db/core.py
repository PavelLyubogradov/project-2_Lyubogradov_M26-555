"""Core logic: table management and CRUD operations on data."""

import json

from primitive_db.constants import (
    COLUMN_TYPE_SEPARATOR,
    FIRST_ID,
    ID_COLUMN,
    ID_TYPE,
    TYPE_CLASSES,
    VALID_TYPES,
)
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data

select_cache = create_cacher()


def invalid_value_error(value: str) -> ValueError:
    """Create an invalid value exception.

    Args:
        value: Value that could not be processed.

    Returns:
        ValueError with a user-friendly message.
    """
    return ValueError(f"Некорректное значение: {value}. Попробуйте снова.")


def format_value(value: int | str | bool) -> str:
    """Format a value the same way the user enters it."""
    return json.dumps(value, ensure_ascii=False)


def format_columns(schema: dict[str, str]) -> str:
    """Format a table schema as a string like "ID:int, name:str"."""
    return ", ".join(
        f"{name}{COLUMN_TYPE_SEPARATOR}{column_type}"
        for name, column_type in schema.items()
    )


def table_exists(metadata: dict, table_name: str) -> bool:
    """Check that a table exists and report if it does not.

    Args:
        metadata: Current database metadata.
        table_name: Table name.

    Returns:
        True if the table exists.
    """
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return False
    return True


def parse_columns(columns: list[str]) -> dict[str, str]:
    """Parse column definitions of the form "name:type".

    Args:
        columns: Column definitions from the create_table command.

    Returns:
        Dict {column_name: type}.

    Raises:
        ValueError: If a column definition is invalid or duplicated.
    """
    schema: dict[str, str] = {}
    for column in columns:
        name, separator, column_type = column.partition(COLUMN_TYPE_SEPARATOR)
        if (
            not separator
            or not name.isidentifier()
            or column_type not in VALID_TYPES
            or name in schema
        ):
            raise invalid_value_error(column)
        schema[name] = column_type
    return schema


@handle_db_errors
def create_table(metadata: dict, table_name: str, columns: list[str]) -> dict | None:
    """Create a table and add its definition to the metadata.

    The ID:int column is prepended automatically if the user did not
    specify it.

    Args:
        metadata: Current database metadata.
        table_name: Name of the new table.
        columns: Column definitions of the form "name:type".

    Returns:
        Updated metadata, or None if the table already exists.

    Raises:
        ValueError: If the table name or column definitions are invalid.
    """
    if not table_name.isidentifier():
        raise invalid_value_error(table_name)
    if table_name in metadata:
        print(f'Ошибка: Таблица "{table_name}" уже существует.')
        return None

    schema = parse_columns(columns)
    id_type = schema.pop(ID_COLUMN, ID_TYPE)
    if id_type != ID_TYPE:
        raise invalid_value_error(f"{ID_COLUMN}{COLUMN_TYPE_SEPARATOR}{id_type}")
    if not schema:
        raise invalid_value_error(
            f"{' '.join(columns)} (нужен хотя бы один столбец, кроме {ID_COLUMN})"
        )

    metadata[table_name] = {ID_COLUMN: ID_TYPE, **schema}
    columns_text = format_columns(metadata[table_name])
    print(f'Таблица "{table_name}" успешно создана со столбцами: {columns_text}')
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata: dict, table_name: str) -> dict | None:
    """Remove a table from the metadata.

    Args:
        metadata: Current database metadata.
        table_name: Name of the table to drop.

    Returns:
        Updated metadata, or None if the table does not exist.
    """
    if not table_exists(metadata, table_name):
        return None
    del metadata[table_name]
    print(f'Таблица "{table_name}" успешно удалена.')
    return metadata


def list_tables(metadata: dict) -> list[str]:
    """Return the names of all tables.

    Args:
        metadata: Current database metadata.

    Returns:
        List of table names.
    """
    return list(metadata)


def check_value_type(column: str, column_type: str, value: int | str | bool) -> None:
    """Check that a value matches the column type.

    Args:
        column: Column name.
        column_type: Column type from the schema.
        value: Value to check.

    Raises:
        ValueError: If the value type does not match the column type.
    """
    # type() instead of isinstance: bool is a subclass of int, and True
    # must not pass the check for an int column.
    if type(value) is not TYPE_CLASSES[column_type]:
        raise invalid_value_error(
            f"{format_value(value)} (столбец {column} имеет тип {column_type})"
        )


@handle_db_errors
def validate_clause(metadata: dict, table_name: str, clause: dict) -> bool:
    """Check that the clause columns exist and the values have the right type.

    Args:
        metadata: Current database metadata.
        table_name: Table name.
        clause: Condition or assignments of the form {column: value}.

    Returns:
        True if the clause is valid.

    Raises:
        KeyError: If the table has no such column.
        ValueError: If the value type does not match the column type.
    """
    schema = metadata[table_name]
    for column, value in clause.items():
        if column not in schema:
            raise KeyError(column)
        check_value_type(column, schema[column], value)
    return True


def matches(record: dict, where_clause: dict | None) -> bool:
    """Check that a record satisfies the where clause.

    Args:
        record: Table record.
        where_clause: Condition {column: value} or None.

    Returns:
        True if there is no condition or all its fields match.
    """
    if not where_clause:
        return True
    return all(record.get(column) == value for column, value in where_clause.items())


def find_matching(table_data: list[dict], where_clause: dict | None) -> list[dict]:
    """Return the records that satisfy the where clause.

    Args:
        table_data: Table records.
        where_clause: Condition {column: value} or None.

    Returns:
        Matching records.
    """
    return [record for record in table_data if matches(record, where_clause)]


@handle_db_errors
@log_time
def insert(metadata: dict, table_name: str, values: list) -> list[dict] | None:
    """Add a record to the table with an auto-generated ID.

    Args:
        metadata: Current database metadata.
        table_name: Table name.
        values: Values for all columns except ID, in schema order.

    Returns:
        Updated table records, or None if the table does not exist.

    Raises:
        ValueError: If the number or types of values do not match the schema.
    """
    if not table_exists(metadata, table_name):
        return None
    columns = {
        name: column_type
        for name, column_type in metadata[table_name].items()
        if name != ID_COLUMN
    }
    if len(values) != len(columns):
        raise invalid_value_error(
            f"ожидается значений: {len(columns)} ({format_columns(columns)}), "
            f"получено: {len(values)}"
        )
    for (column, column_type), value in zip(columns.items(), values):
        check_value_type(column, column_type, value)

    table_data = load_table_data(table_name)
    last_id = max((record[ID_COLUMN] for record in table_data), default=FIRST_ID - 1)
    new_id = last_id + 1
    table_data.append({ID_COLUMN: new_id, **dict(zip(columns, values))})
    print(f'Запись с ID={new_id} успешно добавлена в таблицу "{table_name}".')
    return table_data


@handle_db_errors
@log_time
def select(table_data: list[dict], where_clause: dict | None = None) -> list[dict]:
    """Read table records.

    Args:
        table_data: Table records.
        where_clause: Condition {column: value}; if omitted, all records
            are returned.

    Returns:
        Matching records.
    """
    # The key includes the data itself, so after the table changes a stale
    # result will not be taken from the cache.
    cache_key = json.dumps([table_data, where_clause], ensure_ascii=False)
    return select_cache(cache_key, lambda: find_matching(table_data, where_clause))


@handle_db_errors
def update(table_data: list[dict], set_clause: dict, where_clause: dict) -> list[dict]:
    """Update fields of the records that satisfy the condition.

    Args:
        table_data: Table records.
        set_clause: New values {column: value}.
        where_clause: Condition {column: value}.

    Returns:
        Modified table records.

    Raises:
        ValueError: If an attempt is made to change the ID column.
    """
    if ID_COLUMN in set_clause:
        raise invalid_value_error(f"{ID_COLUMN} (этот столбец нельзя изменять)")
    for record in find_matching(table_data, where_clause):
        record.update(set_clause)
    return table_data


@handle_db_errors
@confirm_action("удаление записи")
def delete(table_data: list[dict], where_clause: dict) -> list[dict]:
    """Delete the records that satisfy the condition.

    Args:
        table_data: Table records.
        where_clause: Condition {column: value}.

    Returns:
        Table records without the deleted ones.
    """
    return [record for record in table_data if not matches(record, where_clause)]
