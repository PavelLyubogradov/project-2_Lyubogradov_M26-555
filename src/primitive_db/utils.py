"""Helper functions for working with the file system."""

import json
import os

from primitive_db.constants import (
    DATA_DIR,
    DATA_FILE_EXTENSION,
    FILE_ENCODING,
    JSON_INDENT,
)


def load_json(filepath: str, default: dict | list) -> dict | list:
    """Load data from a JSON file.

    Args:
        filepath: Path to the file.
        default: Value returned if the file does not exist.

    Returns:
        File contents or the default value.
    """
    try:
        with open(filepath, encoding=FILE_ENCODING) as file:
            return json.load(file)
    except FileNotFoundError:
        return default


def save_json(filepath: str, data: dict | list) -> None:
    """Save data to a JSON file.

    Args:
        filepath: Path to the file.
        data: Data to save.
    """
    with open(filepath, "w", encoding=FILE_ENCODING) as file:
        json.dump(data, file, ensure_ascii=False, indent=JSON_INDENT)


def load_metadata(filepath: str) -> dict:
    """Load database metadata from a JSON file.

    Args:
        filepath: Path to the metadata file.

    Returns:
        Metadata dict, or an empty dict if the file does not exist yet.
    """
    return load_json(filepath, {})


def save_metadata(filepath: str, data: dict) -> None:
    """Save database metadata to a JSON file.

    Args:
        filepath: Path to the metadata file.
        data: Metadata to save.
    """
    save_json(filepath, data)


def get_table_path(table_name: str) -> str:
    """Return the path to a table's data file.

    Args:
        table_name: Table name.

    Returns:
        Path of the form data/<table_name>.json.
    """
    return os.path.join(DATA_DIR, f"{table_name}{DATA_FILE_EXTENSION}")


def load_table_data(table_name: str) -> list[dict]:
    """Load a table's records from its JSON file.

    Args:
        table_name: Table name.

    Returns:
        List of records, or an empty list if there is no data yet.
    """
    return load_json(get_table_path(table_name), [])


def save_table_data(table_name: str, data: list[dict]) -> None:
    """Save a table's records to its JSON file.

    Args:
        table_name: Table name.
        data: Table records.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    save_json(get_table_path(table_name), data)


def delete_table_data(table_name: str) -> None:
    """Delete a table's data file if it exists.

    Args:
        table_name: Table name.
    """
    table_path = get_table_path(table_name)
    if os.path.exists(table_path):
        os.remove(table_path)
