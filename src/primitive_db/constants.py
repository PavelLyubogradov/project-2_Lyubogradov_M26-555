"""Application constants: file paths, data types and prompt texts."""

META_FILE = "db_meta.json"
DATA_DIR = "data"
DATA_FILE_EXTENSION = ".json"
FILE_ENCODING = "utf-8"
JSON_INDENT = 4

ID_COLUMN = "ID"
ID_TYPE = "int"
FIRST_ID = 1
COLUMN_TYPE_SEPARATOR = ":"
TYPE_CLASSES = {"int": int, "str": str, "bool": bool}
VALID_TYPES = tuple(TYPE_CLASSES)

TRUE_LITERAL = "true"
FALSE_LITERAL = "false"
QUOTE_CHARS = ("'", '"')
PUNCTUATION_CHARS = "(),="
ASSIGNMENT_OPERATOR = "="
LIST_SEPARATOR = ","
OPEN_BRACKET = "("
CLOSE_BRACKET = ")"
CONDITION_SEPARATOR = "and"

COMMAND_PROMPT = ">>> Введите команду: "
EXIT_COMMAND = "exit"

KEYWORD_INTO = "into"
KEYWORD_VALUES = "values"
KEYWORD_FROM = "from"
KEYWORD_WHERE = "where"
KEYWORD_SET = "set"
EMPTY_PLACEHOLDER = "<пусто>"

CONFIRM_YES = "y"
TIME_PRECISION = 3
