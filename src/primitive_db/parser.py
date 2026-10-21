"""Parsing of complex commands: insert values and where/set clauses."""

import shlex

from primitive_db.constants import (
    ASSIGNMENT_OPERATOR,
    CLOSE_BRACKET,
    CONDITION_SEPARATOR,
    EMPTY_PLACEHOLDER,
    FALSE_LITERAL,
    KEYWORD_FROM,
    KEYWORD_INTO,
    KEYWORD_SET,
    KEYWORD_VALUES,
    KEYWORD_WHERE,
    LIST_SEPARATOR,
    OPEN_BRACKET,
    PUNCTUATION_CHARS,
    QUOTE_CHARS,
    TRUE_LITERAL,
)
from primitive_db.core import invalid_value_error


def tokenize(text: str) -> list[str]:
    """Split text into tokens, keeping quotes around string values.

    Args:
        text: Command text or part of it.

    Returns:
        List of tokens; parentheses, commas and "=" are separate tokens.

    Raises:
        ValueError: If the text contains an unclosed quote.
    """
    lexer = shlex.shlex(text, posix=False, punctuation_chars=PUNCTUATION_CHARS)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        raise invalid_value_error(text) from None


def split_arguments(user_input: str) -> list[str]:
    """Split a command into arguments, stripping quotes (like shlex.split).

    Args:
        user_input: Entered command.

    Returns:
        List of command arguments.

    Raises:
        ValueError: If the command contains an unclosed quote.
    """
    try:
        return shlex.split(user_input)
    except ValueError:
        raise invalid_value_error(user_input) from None


def is_quoted(token: str) -> bool:
    """Check that the token is a quoted string."""
    return len(token) >= 2 and token[0] in QUOTE_CHARS and token[-1] == token[0]


def parse_value(token: str) -> int | str | bool:
    """Convert a token to a Python value.

    Strings must be quoted, booleans must be true or false, and everything
    else is treated as an integer.

    Args:
        token: Token holding the value.

    Returns:
        Value of type str, bool or int.

    Raises:
        ValueError: If the token is not a valid value.
    """
    if is_quoted(token):
        return token[1:-1]
    if token.lower() == TRUE_LITERAL:
        return True
    if token.lower() == FALSE_LITERAL:
        return False
    try:
        return int(token)
    except ValueError:
        raise invalid_value_error(token) from None


def split_tokens(tokens: list[str], separator: str) -> list[list[str]]:
    """Split a list of tokens into groups by a separator.

    Args:
        tokens: Tokens to split.
        separator: Separator token (compared case-insensitively).

    Returns:
        List of token groups.
    """
    groups: list[list[str]] = [[]]
    for token in tokens:
        if token.lower() == separator:
            groups.append([])
        else:
            groups[-1].append(token)
    return groups


def parse_assignments(tokens: list[str], separator: str) -> dict:
    """Parse expressions of the form "column = value".

    Args:
        tokens: Expression tokens.
        separator: Separator between expressions ("," or "and").

    Returns:
        Dict {column: value}.

    Raises:
        ValueError: If an expression is malformed.
    """
    result = {}
    for group in split_tokens(tokens, separator):
        if (
            len(group) != 3
            or not group[0].isidentifier()
            or group[1] != ASSIGNMENT_OPERATOR
        ):
            raise invalid_value_error(join_tokens(group) or EMPTY_PLACEHOLDER)
        result[group[0]] = parse_value(group[2])
    return result


def parse_where(condition: str) -> dict:
    """Parse a where clause, e.g. 'age = 28' -> {'age': 28}.

    Multiple conditions are combined with and.

    Args:
        condition: Condition text.

    Returns:
        Dict {column: value}.

    Raises:
        ValueError: If the condition is malformed.
    """
    return parse_assignments(tokenize(condition), CONDITION_SEPARATOR)


def parse_set(assignments: str) -> dict:
    """Parse a set clause, e.g. 'name = "Ivan", age = 30'.

    Args:
        assignments: Comma-separated assignments text.

    Returns:
        Dict {column: new_value}.

    Raises:
        ValueError: If an assignment is malformed.
    """
    return parse_assignments(tokenize(assignments), LIST_SEPARATOR)


def parse_values(values: str) -> list:
    """Parse an insert values list, e.g. '("Sergei", 28, true)'.

    Args:
        values: Comma-separated values text in parentheses.

    Returns:
        List of values.

    Raises:
        ValueError: If the values are malformed.
    """
    tokens = tokenize(values)
    if not tokens or tokens[0] != OPEN_BRACKET or tokens[-1] != CLOSE_BRACKET:
        raise invalid_value_error(values)
    result = []
    for group in split_tokens(tokens[1:-1], LIST_SEPARATOR):
        if len(group) != 1:
            raise invalid_value_error(join_tokens(group) or EMPTY_PLACEHOLDER)
        result.append(parse_value(group[0]))
    return result


def find_keyword(tokens: list[str], keyword: str) -> int:
    """Find the position of a keyword among the tokens.

    Args:
        tokens: Command tokens.
        keyword: Keyword to look for (case-insensitive).

    Returns:
        Index of the keyword, or -1 if it is absent.
    """
    for index, token in enumerate(tokens):
        if token.lower() == keyword:
            return index
    return -1


def has_keyword(tokens: list[str], index: int, keyword: str) -> bool:
    """Check that the keyword is at the given index."""
    return index < len(tokens) and tokens[index].lower() == keyword


def get_table_name(tokens: list[str], index: int, user_input: str) -> str:
    """Return the table name at the given index.

    Args:
        tokens: Command tokens.
        index: Position of the table name.
        user_input: Original command, used in the error message.

    Returns:
        Table name.

    Raises:
        ValueError: If the table name is missing or invalid.
    """
    if index >= len(tokens) or not tokens[index].isidentifier():
        raise invalid_value_error(user_input)
    return tokens[index]


def join_tokens(tokens: list[str]) -> str:
    """Join tokens back into a string for re-parsing."""
    return " ".join(tokens)


def parse_insert_command(user_input: str) -> tuple[str, list]:
    """Parse the command insert into <table> values (<values>).

    Args:
        user_input: Entered command.

    Returns:
        Tuple (table_name, values_list).

    Raises:
        ValueError: If the command is malformed.
    """
    tokens = tokenize(user_input)
    if not has_keyword(tokens, 1, KEYWORD_INTO):
        raise invalid_value_error(user_input)
    table_name = get_table_name(tokens, 2, user_input)
    if not has_keyword(tokens, 3, KEYWORD_VALUES):
        raise invalid_value_error(user_input)
    return table_name, parse_values(join_tokens(tokens[4:]))


def parse_select_command(user_input: str) -> tuple[str, dict | None]:
    """Parse the command select from <table> [where <condition>].

    Args:
        user_input: Entered command.

    Returns:
        Tuple (table_name, where_clause or None).

    Raises:
        ValueError: If the command is malformed.
    """
    tokens = tokenize(user_input)
    if not has_keyword(tokens, 1, KEYWORD_FROM):
        raise invalid_value_error(user_input)
    table_name = get_table_name(tokens, 2, user_input)
    condition_tokens = tokens[3:]
    if not condition_tokens:
        return table_name, None
    if not has_keyword(condition_tokens, 0, KEYWORD_WHERE):
        raise invalid_value_error(user_input)
    return table_name, parse_where(join_tokens(condition_tokens[1:]))


def parse_update_command(user_input: str) -> tuple[str, dict, dict]:
    """Parse the command update <table> set <assignments> where <condition>.

    Args:
        user_input: Entered command.

    Returns:
        Tuple (table_name, set_dict, where_dict).

    Raises:
        ValueError: If the command is malformed.
    """
    tokens = tokenize(user_input)
    table_name = get_table_name(tokens, 1, user_input)
    where_index = find_keyword(tokens, KEYWORD_WHERE)
    if not has_keyword(tokens, 2, KEYWORD_SET) or where_index == -1:
        raise invalid_value_error(user_input)
    set_clause = parse_set(join_tokens(tokens[3:where_index]))
    where_clause = parse_where(join_tokens(tokens[where_index + 1 :]))
    return table_name, set_clause, where_clause


def parse_delete_command(user_input: str) -> tuple[str, dict]:
    """Parse the command delete from <table> where <condition>.

    Args:
        user_input: Entered command.

    Returns:
        Tuple (table_name, where_dict).

    Raises:
        ValueError: If the command is malformed.
    """
    tokens = tokenize(user_input)
    if not has_keyword(tokens, 1, KEYWORD_FROM):
        raise invalid_value_error(user_input)
    table_name = get_table_name(tokens, 2, user_input)
    if not has_keyword(tokens, 3, KEYWORD_WHERE):
        raise invalid_value_error(user_input)
    return table_name, parse_where(join_tokens(tokens[4:]))
