#!/usr/bin/env python3
"""Export typos findings into a review JSONL with conservative triage."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import sys

LANGUAGE_BY_EXTENSION = {
    ".go": "go",
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".ts": "javascript",
    ".jsx": "javascript", ".tsx": "javascript", ".mjs": "javascript",
    ".rs": "rust",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".hpp": "cpp", ".hxx": "cpp",
    ".java": "java", ".jav": "java",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala",
    ".cs": "csharp",
    ".lua": "lua",
    ".r": "rlang", ".R": "rlang",
    ".sql": "sql",
    ".yml": "yaml", ".yaml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml", ".xsl": "xml", ".xsd": "xml",
    ".md": "markdown", ".mdx": "markdown",
    ".proto": "protobuf",
    ".graphql": "graphql", ".gql": "graphql",
    ".cmake": "cmake",
    ".dockerfile": "dockerfile",
    ".tf": "terraform", ".tfvars": "terraform",
    ".css": "css", ".scss": "css", ".less": "css",
    ".html": "html", ".htm": "html",
    ".vue": "vue", ".svelte": "svelte",
}

LANGUAGE_KEYWORDS = {
    "go": {
        # keywords
        "break", "case", "chan", "const", "continue", "default", "defer",
        "else", "fallthrough", "for", "func", "go", "goto", "if", "import",
        "interface", "map", "package", "range", "return", "select", "struct",
        "switch", "type", "var",
        # built-in functions
        "append", "cap", "close", "complex", "copy", "delete", "imag", "len",
        "make", "new", "panic", "print", "println", "real", "recover",
        # built-in types / predeclared identifiers
        "bool", "byte", "complex64", "complex128", "error", "float32",
        "float64", "int", "int8", "int16", "int32", "int64", "rune", "string",
        "uint", "uint8", "uint16", "uint32", "uint64", "uintptr",
        "iota", "nil", "true", "false",
        # common Go idioms / abbreviations
        "err", "fmt", "impl", "init", "ctx", "buf", "req", "resp", "done",
        "args", "goroutine", "mutex", "sync", "unmarshal", "marshal",
        "godoc", "streq", "gob", "suffixs", "preifx",
    },
    "python": {
        # keywords
        "false", "none", "true", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else", "except",
        "finally", "for", "from", "global", "if", "import", "in", "is",
        "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
        "try", "while", "with", "yield",
        # built-in functions
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
        "callable", "chr", "classmethod", "compile", "complex", "delattr",
        "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter",
        "float", "format", "frozenset", "getattr", "globals", "hasattr",
        "hash", "hex", "id", "input", "int", "isinstance", "issubclass",
        "iter", "len", "list", "locals", "map", "max", "memoryview",
        "min", "next", "object", "oct", "open", "ord", "pow", "print",
        "property", "range", "repr", "reversed", "round", "set", "setattr",
        "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple",
        "type", "vars", "zip",
        # common idioms
        "self", "cls", "kwargs", "args", "mro", "coro",
        "__init__", "__name__", "__main__", "__all__", "__file__",
        "__dict__", "__class__", "__bases__", "__mro__",
        "__slots__", "__call__", "__iter__", "__next__", "__str__",
        "__repr__", "__len__", "__getitem__", "__setitem__",
        "__delitem__", "__contains__", "__enter__", "__exit__",
    },
    "javascript": {
        # keywords / reserved words
        "async", "await", "break", "case", "catch", "class", "const",
        "continue", "debugger", "default", "delete", "do", "else", "enum",
        "export", "extends", "false", "finally", "for", "function", "if",
        "import", "in", "instanceof", "let", "new", "null", "return",
        "super", "switch", "this", "throw", "true", "try", "typeof",
        "undefined", "var", "void", "while", "with", "yield", "of",
        "from", "as", "get", "set", "static", "implements", "interface",
        "package", "private", "protected", "public",
        # built-ins
        "nan", "infinity", "isnan", "isfinite", "parseint", "parsefloat",
        "eval", "decodeuri", "encodeuri",
        # common JS idioms
        "req", "res", "ctx", "args", "fn", "cb", "err", "buf", "done",
        "promise", "async", "await", "thenable", "esmodule", "commonjs",
        "nodejs", "vdom", "jsx", "tsx",
    },
    "rust": {
        # keywords
        "as", "async", "await", "break", "const", "continue", "crate",
        "dyn", "else", "enum", "extern", "false", "fn", "for", "if",
        "impl", "in", "let", "loop", "match", "mod", "move", "mut",
        "pub", "ref", "return", "self", "static", "struct", "super",
        "trait", "true", "type", "union", "unsafe", "use", "where",
        "while", "yield",
        # built-in types
        "bool", "char", "f32", "f64", "i8", "i16", "i32", "i64", "i128",
        "isize", "str", "u8", "u16", "u32", "u64", "u128", "usize",
        # common Rust idioms
        "deref", "repr", "mutex", "r#", "cstr", "osstr", "pathbuf",
        "arc", "rc", "box", "cell", "refcell", "pin", "unsafecell",
        "vec", "hashmap", "hashset", "btreemap", "btreeset",
        "println", "eprintln", "format", "writeln", "unwrap",
        "expect", "ok", "some", "none",
        "tokio", "serde", "reqwest",
    },
    "shell": {
        "usr", "bin", "env", "echo", "grep", "awk", "sed", "then",
        "elif", "esac", "fi", "done", "uname", "chmod", "chown",
        "basename", "dirname", "readlink", "realpath",
        "pid", "uid", "gid", "stdin", "stdout", "stderr",
        "ifs", "eof", "eol",
        "apt", "yum", "dnf", "brew", "npm", "pip", "cargo",
    },
    "c": {
        "auto", "break", "case", "char", "const", "continue", "default",
        "do", "double", "else", "enum", "extern", "float", "for", "goto",
        "if", "inline", "int", "long", "register", "restrict", "return",
        "short", "signed", "sizeof", "static", "struct", "switch",
        "typedef", "union", "unsigned", "void", "volatile", "while",
        "null", "nullptr", "bool", "complex", "imaginary",
        "intptr", "uintptr", "ptrdiff", "ssize",
        "size_t", "ssize_t", "intptr_t", "uintptr_t", "ptrdiff_t",
        "intmax_t", "uintmax_t",
        "memcpy", "memset", "memmove", "memcmp", "strlen",
        "strcpy", "strncpy", "strcmp", "strncmp", "strcat",
        "malloc", "calloc", "realloc", "free",
        "printf", "fprintf", "sprintf", "snprintf",
        "errno", "stdout", "stderr", "stdin", "eof",
    },
    "cpp": {
        "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand",
        "bitor", "bool", "break", "case", "catch", "char", "char8_t",
        "char16_t", "char32_t", "class", "compl", "concept", "const",
        "consteval", "constexpr", "constinit", "const_cast", "continue",
        "co_await", "co_return", "co_yield", "decltype", "default",
        "delete", "do", "double", "dynamic_cast", "else", "enum",
        "explicit", "export", "extern", "false", "float", "for", "friend",
        "goto", "if", "inline", "int", "long", "mutable", "namespace",
        "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or",
        "or_eq", "private", "protected", "public", "register",
        "reinterpret_cast", "requires", "return", "short", "signed",
        "sizeof", "static", "static_assert", "static_cast", "struct",
        "switch", "template", "this", "thread_local", "throw", "true",
        "try", "typedef", "typeid", "typename", "union", "unsigned",
        "using", "virtual", "void", "volatile", "wchar_t", "while",
        "xor", "xor_eq",
        "nullptr", "std", "stl", "cout", "cin", "cerr", "endl",
        "istream", "ostream", "iostream", "fstream", "sstream",
        "vector", "deque", "list", "map", "set", "unordered_map",
        "unordered_set", "pair", "tuple", "optional", "variant",
        "string", "wstring", "string_view", "span",
        "shared_ptr", "unique_ptr", "weak_ptr", "make_shared",
        "make_unique", "enable_shared_from_this",
        "move", "forward", "emplace", "emplace_back", "push_back",
        "pop_back", "begin", "end", "cbegin", "cend", "rbegin", "rend",
        "size", "empty", "clear", "reserve", "resize", "capacity",
        "atoi", "atol", "atof", "itoa", "strtol", "strtod",
        "snprintf",
    },
    "java": {
        "abstract", "assert", "boolean", "break", "byte", "case", "catch",
        "char", "class", "const", "continue", "default", "do", "double",
        "else", "enum", "extends", "false", "final", "finally", "float",
        "for", "goto", "if", "implements", "import", "instanceof", "int",
        "interface", "long", "native", "new", "null", "package", "private",
        "protected", "public", "return", "short", "static", "strictfp",
        "super", "switch", "synchronized", "this", "throw", "throws",
        "transient", "true", "try", "void", "volatile", "while", "var",
        "record", "sealed", "permits", "yield", "module", "exports",
        "requires", "opens", "to", "with", "provides", "uses",
        "string", "integer", "long", "double", "float", "boolean",
        "byte", "short", "character", "object", "class", "system",
        "out", "err", "in",
        "arraylist", "hashmap", "hashset", "linkedlist", "treemap",
        "treeset", "concurrenthashmap", "atomicinteger",
        "stream", "optional", "collectors", "predicate",
        "function", "supplier", "consumer", "biconsumer",
        "override", "synchronized", "transient", "volatile",
        "npe", "jvm", "jre", "jdk", "pojo", "dto", "dao",
        "servlet", "jsp", "ejb", "jpa", "jdbc", "jta", "jms",
        "spring", "autowired", "component", "service", "repository",
        "controller", "bean", "lombok", "getter", "setter",
    },
    "ruby": {
        "begin", "break", "case", "class", "def", "do", "else", "elsif",
        "end", "ensure", "false", "for", "if", "in", "module", "next",
        "nil", "not", "or", "redo", "rescue", "retry", "return", "self",
        "super", "then", "true", "undef", "unless", "until", "when",
        "while", "yield", "and",
        "attr", "attr_accessor", "attr_reader", "attr_writer",
        "puts", "print", "gets", "chomp", "each", "map", "select",
        "reject", "inject", "reduce", "collect",
        "symbol", "hash", "array", "string", "integer", "float",
        "proc", "lambda", "block",
    },
    "php": {
        "abstract", "and", "array", "as", "break", "callable", "case",
        "catch", "class", "clone", "const", "continue", "declare",
        "default", "die", "do", "echo", "else", "elseif", "empty",
        "enddeclare", "endfor", "endforeach", "endif", "endswitch",
        "endwhile", "eval", "exit", "extends", "final", "finally", "fn",
        "for", "foreach", "function", "global", "goto", "if", "implements",
        "include", "include_once", "instanceof", "insteadof", "interface",
        "isset", "list", "match", "namespace", "new", "or", "print",
        "private", "protected", "public", "readonly", "require",
        "require_once", "return", "static", "switch", "throw", "trait",
        "try", "unset", "use", "var", "while", "xor", "yield",
        "true", "false", "null", "void", "never", "mixed", "bool",
        "int", "float", "string", "array", "object", "callable", "iterable",
        "self", "parent", "this",
    },
    "swift": {
        "actor", "async", "await", "break", "case", "catch", "class",
        "continue", "default", "defer", "deinit", "do", "else", "enum",
        "extension", "fallthrough", "false", "for", "func", "guard",
        "if", "import", "in", "inout", "init", "internal", "is", "let",
        "nil", "operator", "private", "protocol", "public", "repeat",
        "rethrows", "return", "self", "static", "struct", "subscript",
        "super", "switch", "throw", "throws", "true", "try", "typealias",
        "var", "where", "while",
        "anyobject", "associatedtype", "available", "convenience",
        "didSet", "dynamic", "fileprivate", "final", "get", "indirect",
        "infix", "lazy", "left", "mutating", "none", "nonmutating",
        "open", "optional", "override", "postfix", "precedence",
        "prefix", "required", "right", "set", "some", "unowned",
        "weak", "willSet",
        "string", "int", "double", "float", "bool", "character",
        "array", "dictionary", "set", "optional", "result",
        "uikit", "swiftui", "combine", "coredata", "xcode",
        "nsstring", "nsnumber", "nsarray", "nsdictionary",
        "nsset", "nsdata", "nsdate", "nsobject", "nsnotification",
    },
    "kotlin": {
        "abstract", "actual", "annotation", "as", "break", "by", "class",
        "companion", "const", "continue", "data", "do", "dynamic", "else",
        "enum", "expect", "external", "false", "field", "file", "final",
        "finally", "for", "fun", "get", "if", "import", "in", "infix",
        "init", "inline", "inner", "interface", "internal", "is", "it",
        "lateinit", "noinline", "null", "object", "open", "operator",
        "out", "override", "package", "param", "private", "property",
        "protected", "public", "receiver", "reified", "return", "sealed",
        "set", "setparam", "super", "suspend", "tailrec", "this", "throw",
        "true", "try", "typealias", "typeof", "val", "var", "vararg",
        "when", "where", "while",
        "int", "long", "short", "byte", "double", "float", "boolean",
        "char", "string", "unit", "nothing", "any",
        "arraylist", "hashmap", "hashset", "linkedlist",
        "arrayof", "listof", "setof", "mapof", "mutablelistof",
    },
    "scala": {
        "abstract", "case", "catch", "class", "def", "do", "else",
        "extends", "false", "final", "finally", "for", "forsome", "given",
        "if", "implicit", "import", "lazy", "match", "new", "null",
        "object", "override", "package", "private", "protected", "return",
        "sealed", "super", "then", "this", "throw", "trait", "true", "try",
        "type", "using", "val", "var", "while", "with", "yield",
        "int", "long", "short", "byte", "double", "float", "boolean",
        "char", "string", "unit", "nothing", "any", "anyval", "anyref",
        "list", "seq", "set", "map", "vector", "array", "option",
        "some", "none", "either", "left", "right", "future",
        "future", "promise", "executioncontext",
    },
    "csharp": {
        "abstract", "as", "base", "bool", "break", "byte", "case", "catch",
        "char", "checked", "class", "const", "continue", "decimal",
        "default", "delegate", "do", "double", "else", "enum", "event",
        "explicit", "extern", "false", "finally", "fixed", "float", "for",
        "foreach", "goto", "if", "implicit", "in", "int", "interface",
        "internal", "is", "lock", "long", "namespace", "new", "null",
        "object", "operator", "out", "override", "params", "private",
        "protected", "public", "readonly", "record", "ref", "return",
        "sbyte", "sealed", "short", "sizeof", "stackalloc", "static",
        "string", "struct", "switch", "this", "throw", "true", "try",
        "typeof", "uint", "ulong", "unchecked", "unsafe", "ushort",
        "using", "var", "virtual", "void", "volatile", "while",
        "async", "await", "dynamic", "from", "get", "join", "let",
        "nameof", "not", "notnull", "or", "orderby", "partial", "remove",
        "select", "set", "value", "when", "where", "yield",
        "ienumerable", "ilist", "idictionary", "ienumerator",
        "list", "dictionary", "hashset", "queue", "stack",
        "task", "valuetask", "action", "func", "predicate",
        "linq", "entityframework", "nunit", "xunit",
        "aspnet", "mvc", "razor", "blazor", "wpf", "winforms",
        "dto", "poco", "orm",
    },
    "lua": {
        "and", "break", "do", "else", "elseif", "end", "false", "for",
        "function", "goto", "if", "in", "local", "nil", "not", "or",
        "repeat", "return", "then", "true", "until", "while",
        "ipairs", "pairs", "next", "rawget", "rawset", "rawlen",
        "tonumber", "tostring", "type", "assert", "error",
        "pcall", "xpcall", "select", "unpack",
        "string", "table", "math", "io", "os", "debug", "coroutine",
        "setmetatable", "getmetatable",
        "len", "concat", "insert", "remove", "sort",
        "sub", "find", "match", "gmatch", "gsub",
        "format", "rep", "reverse", "upper", "lower",
    },
    "rlang": {
        "if", "else", "for", "while", "repeat", "break", "next",
        "function", "return", "in", "true", "false", "null", "inf",
        "nan", "na", "na_integer", "na_real", "na_complex",
        "na_character", "null", "na",
        "numeric", "integer", "character", "logical", "complex",
        "vector", "list", "matrix", "array", "dataframe", "factor",
        "c", "seq", "rep", "length", "dim", "nrow", "ncol",
        "names", "rownames", "colnames", "dimnames",
        "lapply", "sapply", "vapply", "tapply", "mapply", "rapply",
        "apply", "rowsums", "colsums", "rowmeans", "colmeans",
        "mean", "median", "sd", "var", "sum", "min", "max", "range",
        "subset", "merge", "aggregate", "transform",
        "lm", "glm", "anova", "coef", "residuals", "fitted",
        "rm", "ls", "get", "assign", "exists",
        "plot", "points", "lines", "text", "title", "axis",
        "ggplot", "aes", "geom", "facet",
        "readcsv", "writecsv", "readtable", "writetable",
        "dplyr", "tidyr", "purrr", "tibble", "stringr",
    },
    "sql": {
        "select", "from", "where", "insert", "update", "delete", "create",
        "alter", "drop", "truncate", "merge", "replace", "upsert",
        "into", "values", "set", "table", "view", "index", "constraint",
        "primary", "key", "foreign", "references", "unique", "check",
        "default", "not", "null", "cascade", "restrict",
        "join", "inner", "outer", "left", "right", "full", "cross",
        "on", "and", "or", "in", "between", "like", "is", "exists",
        "order", "by", "asc", "desc", "group", "having", "limit",
        "offset", "fetch", "union", "except", "intersect",
        "begin", "commit", "rollback", "savepoint",
        "integer", "varchar", "char", "text", "boolean", "float",
        "double", "decimal", "numeric", "timestamp", "date", "time",
        "bigint", "smallint", "tinyint", "serial", "bigserial",
        "uuid", "jsonb", "array", "enum", "interval",
        "count", "sum", "avg", "min", "max", "coalesce", "nullif",
        "upper", "lower", "trim", "substring", "concat",
        "postgres", "mysql", "sqlite", "mssql", "oracle",
    },
    "yaml": {
        "true", "false", "yes", "no", "on", "off", "null", "yaml",
        "key", "value", "anchor", "alias", "tag", "merge",
        "env", "dev", "stg", "prod", "prd", "test", "uat",
        "url", "uri", "host", "port", "user", "pass", "auth",
        "name", "type", "image", "version", "replicas",
        "namespace", "deployment", "service", "ingress",
        "configmap", "secret", "pvc", "pv", "nodeport",
        "k8s", "kubernetes", "docker", "pod", "cronjob",
    },
    "toml": {
        "true", "false",
    },
    "json": {
        "true", "false", "null",
    },
    "xml": {
        "xml", "xslt", "xsd", "xpath", "xquery", "xsl",
        "dtd", "cdata", "pcdata", "schema", "namespace",
        "xmlns", "xs", "xsi", "xlink", "soap", "wsdl",
    },
    "markdown": {
        "md", "mdx", "html", "css", "js", "ts", "api", "cli", "url",
        "uri", "http", "https", "ftp", "ssh", "git", "npm", "yaml",
        "json", "xml", "csv", "txt", "pdf", "png", "jpg", "svg",
        "gif", "webp", "mp4", "mp3", "wav", "avi",
        "readme", "changelog", "license", "contributing", "authors",
        "todo", "fixme", "hack", "xxx", "note",
        "github", "gitlab", "bitbucket", "npmjs", "dockerhub",
        "markdown", "commonmark", "gfm",
    },
    "protobuf": {
        "syntax", "package", "import", "option", "message", "enum",
        "service", "rpc", "returns", "stream", "extend", "extensions",
        "reserved", "oneof", "map", "repeated", "required", "optional",
        "bool", "bytes", "string", "int32", "int64", "uint32", "uint64",
        "sint32", "sint64", "fixed32", "fixed64", "sfixed32", "sfixed64",
        "float", "double", "proto3", "proto2", "grpc", "protobuf",
        "any", "timestamp", "duration", "fieldmask", "struct",
        "wrappers", "empty",
    },
    "graphql": {
        "query", "mutation", "subscription", "fragment", "type", "input",
        "interface", "union", "enum", "scalar", "schema", "directive",
        "on", "extend", "implements", "repeatable",
        "int", "float", "string", "boolean", "id",
        "true", "false", "null",
        "gql", "graphql", "resolver", "dataloader",
    },
    "cmake": {
        "cmake", "cmakelists", "cmake_minimum_required", "project",
        "add_executable", "add_library", "add_subdirectory",
        "target_link_libraries", "target_include_directories",
        "target_compile_definitions", "target_compile_options",
        "target_compile_features", "target_sources",
        "set", "unset", "list", "string", "file", "math",
        "if", "else", "elseif", "endif", "foreach", "endforeach",
        "while", "endwhile", "function", "endfunction", "macro",
        "endmacro", "break", "continue", "return",
        "option", "include", "find_package", "find_library",
        "find_path", "find_file", "find_program",
        "install", "export", "configure_file", "message",
        "on", "off", "true", "false", "yes", "no",
        "debug", "release", "minsizerel", "relwithdebinfo",
    },
    "dockerfile": {
        "from", "run", "cmd", "label", "maintainer", "expose", "env",
        "add", "copy", "entrypoint", "volume", "user", "workdir",
        "arg", "onbuild", "stopsignal", "healthcheck", "shell",
        "apt", "yum", "apk", "dnf", "npm", "pip", "cargo",
        "alpine", "debian", "ubuntu", "centos", "slim",
        "libc", "gcc", "g++", "make", "cmake", "autoconf",
        "wget", "curl", "git", "openssh", "ca-certificates",
        "tmp", "var", "usr", "etc", "opt", "srv", "home", "root",
    },
    "terraform": {
        "terraform", "required_providers", "provider", "resource",
        "data", "variable", "output", "locals", "module", "moved",
        "import", "terraform", "backend",
        "for_each", "count", "depends_on", "lifecycle",
        "prevent_destroy", "create_before_destroy", "ignore_changes",
        "provisioner", "connection", "null_resource",
        "cidr", "ipv4", "ipv6", "dns", "tls", "ssl", "ssh", "rdp",
        "aws", "azurerm", "gcp", "google", "oci", "vsphere",
    },
    "css": {
        "px", "em", "rem", "vh", "vw", "vmin", "vmax", "fr", "ch", "ex",
        "rgb", "rgba", "hsl", "hsla", "hex", "url", "var",
        "flex", "grid", "block", "inline", "none", "auto", "inherit",
        "initial", "unset", "revert",
        "serif", "sans-serif", "monospace", "cursive", "fantasy",
        "minmax", "repeat", "auto-fill", "auto-fit",
        "webkit", "moz", "ms", "o",
    },
    "html": {
        "doctype", "html", "head", "body", "title", "meta", "link",
        "style", "script", "div", "span", "p", "a", "img", "ul", "ol",
        "li", "table", "tr", "td", "th", "thead", "tbody", "tfoot",
        "form", "input", "button", "select", "option", "textarea",
        "label", "fieldset", "legend", "nav", "header", "footer",
        "main", "section", "article", "aside", "figure", "figcaption",
        "iframe", "canvas", "svg", "video", "audio", "source", "track",
        "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr", "pre", "code",
        "href", "src", "alt", "id", "class", "style", "type", "name",
        "value", "placeholder", "disabled", "readonly", "required",
        "checked", "selected", "hidden", "charset", "utf-8",
        "onclick", "onchange", "onsubmit", "onload", "onerror",
    },
    "vue": {
        "vue", "template", "script", "style", "scoped", "lang",
        "setup", "reactive", "ref", "computed", "watch", "props",
        "emits", "expose", "slots", "attrs", "provide", "inject",
        "onmounted", "onunmounted", "onupdated", "onbeforemount",
        "onbeforeunmount", "onbeforeupdate", "onerrorcaptured",
        "onrendertracked", "onrendertriggered", "onactivated",
        "ondeactivated", "onserverprefetch",
        "v-if", "v-else", "v-else-if", "v-for", "v-show", "v-model",
        "v-bind", "v-on", "v-slot", "v-text", "v-html", "v-once",
        "v-memo", "v-cloak", "v-pre",
        "vuex", "pinia", "vuerouter", "nuxt", "vitepress",
        "vite", "webpack", "esbuild", "rollup",
    },
    "svelte": {
        "svelte", "script", "style", "lang",
        "onmount", "ondestroy", "beforeupdate", "afterupdate",
        "tick", "setcontext", "getcontext", "hascontext",
        "getallcontexts", "createeventdispatcher",
        "$state", "$derived", "$effect", "$props", "$bindable",
        "$inspect", "$host", "runes",
        "store", "writable", "readable", "derived",
        "each", "if", "else", "await", "then", "catch",
        "animate", "transition", "in", "out",
        "kit", "sveltekit", "vite",
    },
}


def die(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def iter_items(handle):
    for idx, raw in enumerate(handle, 1):
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            die(f"invalid JSON from typos at line {idx}: {exc}")
        if item.get("type") != "typo":
            continue
        if "typo" not in item or "path" not in item:
            continue
        yield item


def line_starts(data: bytes) -> list[int]:
    starts = [0]
    for idx, byte in enumerate(data):
        if byte == 10:
            starts.append(idx + 1)
    return starts


class FileCache:
    def __init__(self) -> None:
        self._cache: dict[str, dict[str, object]] = {}

    def get(self, path: str) -> dict[str, object]:
        cached = self._cache.get(path)
        if cached is not None:
            return cached

        file_path = Path(path)
        try:
            data = file_path.read_bytes()
        except OSError as exc:
            die(f"cannot read source file '{path}': {exc}")

        starts = line_starts(data)
        cached = {"data": data, "starts": starts}
        self._cache[path] = cached
        return cached


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def get_line_context(item: dict[str, object], cache: FileCache) -> dict[str, object]:
    path = str(item.get("path", ""))
    line_num = item.get("line_num")
    byte_offset = item.get("byte_offset")
    typo = str(item.get("typo", ""))
    typo_bytes = typo.encode("utf-8")

    if not isinstance(line_num, int) or line_num < 1:
        return {
            "line_text": "",
            "line_start": None,
            "line_end": None,
            "relative_byte_offset": None,
            "char_index": None,
        }

    cached = cache.get(path)
    data = cached["data"]
    starts = cached["starts"]
    assert isinstance(data, bytes)
    assert isinstance(starts, list)

    if line_num > len(starts):
        return {
            "line_text": "",
            "line_start": None,
            "line_end": None,
            "relative_byte_offset": None,
            "char_index": None,
        }

    line_start = starts[line_num - 1]
    line_end = starts[line_num] if line_num < len(starts) else len(data)
    segment = data[line_start:line_end]
    line_text = decode_text(segment).rstrip("\n")

    relative_byte_offset = None
    char_index = None
    if isinstance(byte_offset, int) and byte_offset >= line_start:
        rel = byte_offset - line_start
        if segment[rel:rel + len(typo_bytes)] == typo_bytes:
            relative_byte_offset = rel
            char_index = len(decode_text(segment[:rel]))

    if relative_byte_offset is None and typo:
        char_index = line_text.find(typo)
        if char_index >= 0:
            relative_byte_offset = len(line_text[:char_index].encode("utf-8"))
        else:
            char_index = None

    return {
        "line_text": line_text,
        "line_start": line_start,
        "line_end": line_end,
        "relative_byte_offset": relative_byte_offset,
        "char_index": char_index,
    }


def detect_test_artifact(path: str) -> bool:
    candidate = Path(path)
    lowered_parts = [part.lower() for part in candidate.parts]
    artifact_dirs = {
        "__snapshots__",
        "__fixtures__",
        "__mocks__",
        "snapshots",
        "fixtures",
        "mocks",
    }
    if any(part in artifact_dirs for part in lowered_parts):
        return True
    return candidate.name.lower().endswith(".snap")


def detect_hex_token(token: str, line_text: str, char_index: int | None) -> bool:
    if re.fullmatch(r"(?:0x)?[0-9a-fA-F]{6,}", token):
        return True
    if char_index is None or not token:
        return False

    start = char_index
    end = char_index + len(token)
    left = line_text[max(0, start - 2):start]
    right = line_text[end:end + 2]
    merged = f"{left}{token}{right}"
    return bool(re.fullmatch(r"(?:0x)?[0-9a-fA-F]{6,}", merged))


def detect_url_or_query(line_text: str, char_index: int | None, token: str) -> tuple[bool, str | None]:
    if char_index is None or not token:
        return False, None

    token_end = char_index + len(token)
    for match in re.finditer(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://\S+", line_text):
        start, end = match.span()
        if start <= char_index < end or start < token_end <= end:
            url_text = match.group(0)
            prefix = line_text[start:char_index]
            suffix = line_text[token_end:end]
            if ("?" in prefix or "&" in prefix) or suffix.startswith("="):
                return True, "query parameter inside URL"
            return True, "inside URL"

    prefix = line_text[:char_index]
    suffix = line_text[token_end:]
    query_key = re.search(r"[?&][^=&\s\"']*$", prefix) and suffix.startswith("=")
    query_value = re.search(r"[?&][^=&\s\"']+=$", prefix)
    if query_key or query_value:
        return True, "query parameter"
    return False, None


def detect_json_key(line_text: str, char_index: int | None, token: str) -> bool:
    if char_index is None or not token:
        return False
    for match in re.finditer(r'"([^"\\]|\\.)*"\s*:', line_text):
        start, end = match.span()
        if start <= char_index < end:
            return True
    return False


def detect_css_class(path: str, line_text: str, char_index: int | None, token: str) -> bool:
    if char_index is None or not token:
        return False

    attr_patterns = (
        r'class(?:Name)?\s*=\s*["\'][^"\']*$',
        r'class(?:Name)?\s*:\s*["\'][^"\']*$',
    )
    prefix = line_text[:char_index]
    for pattern in attr_patterns:
        if re.search(pattern, prefix):
            return True

    stylesheet_suffixes = {".css", ".scss", ".sass", ".less", ".styl"}
    if Path(path).suffix.lower() in stylesheet_suffixes:
        token_end = char_index + len(token)
        for match in re.finditer(r"\.[A-Za-z0-9_-]+", line_text):
            start, end = match.span()
            if start < token_end and char_index < end:
                return True

    return False


def detect_dom_selector(line_text: str, char_index: int | None, token: str) -> bool:
    if char_index is None or not token:
        return False

    prefix = line_text[:char_index]
    selector_calls = (
        "querySelector",
        "querySelectorAll",
        "getElementById",
        "getElementsByClassName",
        "locator(",
        "$(",
        "$$(",
    )
    if any(call in prefix for call in selector_calls):
        return True

    token_end = char_index + len(token)
    for match in re.finditer(r'["\'][^"\']*[.#\[][^"\']*["\']', line_text):
        start, end = match.span()
        if start <= char_index < end or start < token_end <= end:
            return True
    return False


def detect_language(path: str) -> str | None:
    suffix = Path(path).suffix.lower()
    return LANGUAGE_BY_EXTENSION.get(suffix)


def detect_language_keyword(token: str, path: str) -> bool:
    language = detect_language(path)
    if language is None:
        return False
    keywords = LANGUAGE_KEYWORDS.get(language)
    if keywords is None:
        return False
    return token.lower() in keywords


def is_identifier_token(token: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", token))


def split_identifier_words(identifier: str) -> list[str]:
    if not identifier:
        return []

    parts = re.split(r"[_-]+", identifier)
    words: list[str] = []
    for part in parts:
        if not part:
            continue
        camel_parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", part)
        if camel_parts:
            words.extend(camel_parts)
        else:
            words.append(part)
    return words


def abbreviate_identifier(identifier: str) -> str:
    words = split_identifier_words(identifier)
    letters = [word[0].lower() for word in words if word and word[0].isalpha()]
    return "".join(letters)


def choose_rename_candidate(token: str, rhs_text: str) -> str:
    candidates = re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", rhs_text)
    preferred = []
    for candidate in candidates:
        if candidate == token:
            continue
        if len(candidate) <= len(token):
            continue
        preferred.append(candidate)

    token_abbr = token.lower()
    matching = [
        candidate
        for candidate in preferred
        if abbreviate_identifier(candidate) == token_abbr
    ]
    if matching:
        matching.sort(key=len, reverse=True)
        return matching[0]

    return ""


def detect_short_identifier_rename(line_text: str, char_index: int | None, token: str) -> str:
    if char_index is None or len(token) > 3 or not is_identifier_token(token):
        return ""

    escaped = re.escape(token)
    match = re.search(rf"\b(?:const|let|var)\s+({escaped})\b\s*=\s*(.+)", line_text)
    if not match:
        return ""

    start, end = match.span(1)
    if not (start <= char_index < end):
        return ""

    rhs_text = match.group(2).strip()
    return choose_rename_candidate(token, rhs_text)


def choose_word_section(token: str) -> str:
    if re.fullmatch(r"[a-z0-9-]+", token):
        return "default.extend-words"
    return "default.extend-identifiers"


def build_word_snippet(token: str) -> tuple[str, str]:
    section = choose_word_section(token)
    snippet = f"[{section}]\n\"{token}\" = \"{token}\""
    return section, snippet


def build_exclude_snippet(path: str) -> tuple[str, str]:
    target = Path(path)
    lowered_parts = [part.lower() for part in target.parts]
    marker_index = None
    for idx, part in enumerate(lowered_parts):
        if any(key in part for key in ("snapshot", "fixture", "mock")):
            marker_index = idx
            break

    if marker_index is None:
        value = path
    else:
        prefix = Path(*target.parts[: marker_index + 1])
        value = prefix.as_posix()
        if Path(value).suffix:
            pass
        else:
            value = f"{value}/**"

    snippet = f"[files]\nextend-exclude = [\n  \"{value}\"\n]"
    return "files.extend-exclude", snippet


def classify(item: dict[str, object], context: dict[str, object]) -> dict[str, object]:
    path = str(item.get("path", ""))
    token = str(item.get("typo", ""))
    line_text = str(context.get("line_text", ""))
    char_index = context.get("char_index")
    char_index = char_index if isinstance(char_index, int) else None

    if detect_hex_token(token, line_text, char_index):
        return {
            "bucket": "false_positive.hex",
            "status": "FALSE POSITIVE",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "KEEP_SOURCE",
            "reason": "Matched a hexadecimal-like token; technical literals should not be auto-corrected.",
            "rename_candidate": "",
        }

    is_url, url_reason = detect_url_or_query(line_text, char_index, token)
    if is_url:
        return {
            "bucket": "false_positive.url",
            "status": "FALSE POSITIVE",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "KEEP_SOURCE",
            "reason": f"Matched {url_reason}; URLs and query parameters default to false positives.",
            "rename_candidate": "",
        }

    if detect_css_class(path, line_text, char_index, token):
        return {
            "bucket": "false_positive.css_class",
            "status": "FALSE POSITIVE",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "KEEP_SOURCE",
            "reason": "Matched a CSS class or selector-like token; styling identifiers default to false positives.",
            "rename_candidate": "",
        }

    if detect_json_key(line_text, char_index, token):
        return {
            "bucket": "false_positive.json_key",
            "status": "FALSE POSITIVE",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "KEEP_SOURCE",
            "reason": "Matched a JSON key; data/schema keys default to false positives.",
            "rename_candidate": "",
        }

    if detect_dom_selector(line_text, char_index, token):
        return {
            "bucket": "false_positive.dom_selector",
            "status": "FALSE POSITIVE",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "KEEP_SOURCE",
            "reason": "Matched a DOM selector; selector strings default to false positives.",
            "rename_candidate": "",
        }

    rename_candidate = detect_short_identifier_rename(line_text, char_index, token)
    if rename_candidate:
        return {
            "bucket": "manual_review.rename_candidate",
            "status": "PENDING",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "RENAME_SYMBOL",
            "reason": (
                f"Matched a short internal variable name; a semantic rename such as "
                f"'{rename_candidate}' is safer than a spelling auto-fix."
            ),
            "rename_candidate": rename_candidate,
        }

    if len(token) <= 2:
        return {
            "bucket": "manual_review.short_token",
            "status": "PENDING",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "REVIEW_SOURCE",
            "reason": "Matched a very short token; short abbreviations have high false-positive risk, so do not auto-fix.",
            "rename_candidate": "",
        }

    if detect_test_artifact(path):
        return {
            "bucket": "manual_review.test_artifact",
            "status": "PENDING",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "CONSIDER_TYPOS_TOML",
            "reason": "Matched snapshot/fixture/mock data; test artifacts default to manual review instead of auto-fix.",
            "rename_candidate": "",
        }

    language = detect_language(path)
    if language is not None and detect_language_keyword(token, path):
        return {
            "bucket": "false_positive.language_keyword",
            "status": "FALSE POSITIVE",
            "suggested_status": "FALSE POSITIVE",
            "preferred_action": "KEEP_SOURCE",
            "reason": f"`{token}` is a {language} language keyword/builtin/idiom; not a spelling error.",
            "rename_candidate": "",
        }

    return {
        "bucket": "candidate.source_fix",
        "status": "PENDING",
        "suggested_status": "ACCEPT CORRECT",
        "preferred_action": "REVIEW_SOURCE",
        "reason": "No conservative false-positive rule matched; review source context before accepting the suggested fix.",
        "rename_candidate": "",
    }


def load_records(path: Path) -> list[dict[str, object]]:
    cache = FileCache()
    records = []
    occurrence_counts: dict[tuple[str, object, str], int] = {}

    try:
        with path.open("r", encoding="utf-8") as handle:
            for item in iter_items(handle):
                file_path = str(item.get("path", "<unknown>"))
                line_num = item.get("line_num", "?")
                typo = str(item.get("typo", ""))
                corrections = item.get("corrections", []) or []

                key = (file_path, line_num, typo)
                occurrence_index = occurrence_counts.get(key, 0) + 1
                occurrence_counts[key] = occurrence_index

                context = get_line_context(item, cache)
                triage = classify(item, context)

                records.append(
                    {
                        "path": file_path,
                        "line_num": item.get("line_num"),
                        "byte_offset": item.get("byte_offset"),
                        "occurrence_index": occurrence_index,
                        "typo": typo,
                        "corrections": corrections,
                        "status": triage["status"],
                        "correction": "",
                        "reason": triage["reason"],
                        "bucket": triage["bucket"],
                        "suggested_status": triage["suggested_status"],
                        "preferred_action": triage["preferred_action"],
                        "rename_candidate": triage["rename_candidate"],
                        "line_text": context["line_text"],
                        "toml_section": "",
                        "toml_snippet": "",
                    }
                )
    except OSError as exc:
        die(f"cannot read typos output '{path}': {exc}")

    return records


def annotate_toml_advice(records: list[dict[str, object]]) -> list[dict[str, object]]:
    token_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    test_artifact_groups: dict[str, list[dict[str, object]]] = defaultdict(list)

    for record in records:
        typo = str(record["typo"]).lower()
        token_groups[typo].append(record)
        if record["bucket"] == "manual_review.test_artifact":
            test_artifact_groups[str(record["path"])].append(record)

    for typo, items in token_groups.items():
        conservative = [
            item
            for item in items
            if not str(item["bucket"]).startswith("candidate.")
            and item["bucket"] != "manual_review.test_artifact"
            and item["bucket"] != "manual_review.rename_candidate"
        ]
        if len(conservative) < 2:
            continue
        section, snippet = build_word_snippet(str(items[0]["typo"]))
        for item in conservative:
            item["preferred_action"] = "UPDATE_TYPOS_TOML"
            item["toml_section"] = section
            item["toml_snippet"] = snippet
            item["reason"] = (
                f"{item['reason']} Repeated false positive for '{item['typo']}' "
                f"({len(conservative)} hits); prefer `.typos.toml` over editing source one by one."
            )

    if len(test_artifact_groups) >= 1:
        by_pattern: dict[str, tuple[str, str, list[dict[str, object]]]] = {}
        for path, items in test_artifact_groups.items():
            section, snippet = build_exclude_snippet(path)
            key = snippet
            previous = by_pattern.get(key)
            if previous is None:
                by_pattern[key] = (section, snippet, list(items))
            else:
                previous[2].extend(items)

        for section, snippet, items in by_pattern.values():
            if len(items) < 2:
                continue
            for item in items:
                item["preferred_action"] = "UPDATE_TYPOS_TOML"
                item["toml_section"] = section
                item["toml_snippet"] = snippet
                item["reason"] = (
                    f"{item['reason']} Similar hits repeat in test artifacts ({len(items)} hits); "
                    "prefer excluding them in `.typos.toml` before editing fixture data."
                )

    return records


def print_summary(records: list[dict[str, object]]) -> None:
    files = {str(record["path"]) for record in records}
    print(f"Found {len(records)} spelling errors in {len(files)} files.")
    print("")

    counts = Counter(str(record["bucket"]).split(".", 1)[0] for record in records)
    print("Bucket summary:")
    print(f"- candidate source fixes: {counts.get('candidate', 0)}")
    print(f"- default false positives: {counts.get('false_positive', 0)}")
    print(f"- manual review only: {counts.get('manual_review', 0)}")
    print("")

    snippets = []
    seen = set()
    for record in records:
        snippet = str(record["toml_snippet"])
        if not snippet or snippet in seen:
            continue
        seen.add(snippet)
        snippets.append((str(record["typo"]), snippet))

    if snippets:
        print("Suggested `.typos.toml` updates:")
        for typo, snippet in snippets:
            print(f"- For `{typo}`:")
            for line in snippet.splitlines():
                print(f"    {line}")
        print("")


def print_records(records: list[dict[str, object]]) -> None:
    for record in records:
        suggestion_text = ", ".join(record["corrections"])
        print(f"### `{record['path']}`:{record['line_num']}")
        print(f"  **Error**: `{record['typo']}`")
        print(f"  **Suggestions**: [{suggestion_text}]")
        print(f"  **Bucket**: `{record['bucket']}`")
        print(f"  **Suggested Status**: `{record['suggested_status']}`")
        print(f"  **Preferred Action**: `{record['preferred_action']}`")
        print(f"  **Reason**: {record['reason']}")
        if record["rename_candidate"]:
            print(f"  **Rename Candidate**: `{record['rename_candidate']}`")
        line_text = str(record["line_text"]).strip()
        if line_text:
            print(f"  **Line**: `{line_text}`")
        if record["toml_snippet"]:
            print("  **.typos.toml Suggestion**:")
            for line in str(record["toml_snippet"]).splitlines():
                print(f"    {line}")
        print("")


def write_review_file(path: Path, records: list[dict[str, object]]) -> None:
    try:
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    except OSError as exc:
        die(f"cannot write review file '{path}': {exc}")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or len(argv) > 3:
        die("usage: export-review.py <typos-output.jsonl> [review.jsonl]")

    input_path = Path(argv[1])
    review_path = Path(argv[2]) if len(argv) == 3 else None

    records = annotate_toml_advice(load_records(input_path))
    if not records:
        print("Found 0 spelling errors in 0 files.")
        return 0

    print_summary(records)
    print_records(records)

    if review_path is not None:
        write_review_file(review_path, records)
        print(f"Review file written to: {review_path}")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
