"""
A collection of utility wrappers around the Google Work Space Python client.
The goal is to simplify more complicated aspects like authentication, A1 notation,
structures for JSON requests/responses, etc.

Python dataclasses are used for the resource structs and most of the logic is
translating between those and the raw dicts.

Right now Sheets and Calendar are supported.  Calendar is fairly simple so
the operations are methods on the actual dataclass representation.  Sheets
is a bit more complex so has base classes to abstract the representation.
"""
