import re

from typing import Self
from collections.abc import Iterable

from . import GoogleSheetsMaxColumns

class GoogleSheetsA1Notation():
    """
    Class representation of a Google Sheets A1 cell range notation.
    See https://developers.google.com/sheets/api/guides/concepts#:~:text=A1%20notation,an%20absolute%20range%20of%20cells
    For easy manipulation of adding/removing rows and columns and getting
    at numerical coordinate translations.
    A general A1 has the form:

    <title>!<start col><start row>:<end col><end row>

    So some notes on the above:
        All rows are integers, and are 1 based
        All cols are alphabetical A-ZZZ
        The maximum number of cols available is 18278 which corresponds to col ZZZ
        The maximum number of cells available in a sheet is 10 million, so row * col <= 10,000,000.
        So theoretically the maximum number of rows is 10 million with one col but as you can see can vary.
        Start/end cols/rows may not be present, which means 'unbounded' or all.
            So an A1 with just a title and nothing else following means 'all cells'
            A:B means 'all rows in columns A and B
            1:6 means 'all cols and rows 1 through 6
            C2:S means all all cells in cols C through S starting from 2 to the end
            A45 means a single cell of row 45 in col A
            A45:46 means rows 45 and 46 of col A
            ToDo: Can you have unbounded start with a bounded end?  Need to check. 

        title:      The title of a sheet within a spreadsheet.  This may be blank,
                    in which case the '!' delimeter will not be present, which means
                    the first sheet within a spreadshet (ID 0).  A title may be quoted
                    if it contains spaces or other non alphanumeric characters.
        start col:  Starting column of range, must be A-ZZZ or not present if unbounded.
        end col:    Ending column of range, must be A-ZZZ or not present if unbounded.
                    If present it must be 'greater' than start col.
        start row:  Starting row of range or not present if unbounded.
        end row:    Ending row of range, or not present if unbounded.

    Because rows and column indexing is 1-based, a value of 0 in this class signals 'unbounded'.
    """
    # try to catch a whole A1 string here, or as much as possible
    _A1REGEXSTR = r"^\s*((?P<sheet>\w+|\".+\"|\'.+\')!)?((?P<start_col>[A-Z]{0,3})?(?P<start_row>\d+)?:(?P<end_col>[A-Z]{0,3})?(?P<end_row>\d+)?)?\s*$"
    # just trying to catch A-ZZZ for a valid column label
    _A1COLREGEXSTR = r"^[A-Z]{1,3}$"
    # validate a title label
    _A1SHEETREGEXSTR = r"^\s*(\w+|\".+\"|\'.+\')"

    _a1_re = re.compile(_A1REGEXSTR)
    _a1_col_re = re.compile(_A1COLREGEXSTR)
    _a1_sheet_re = re.compile(_A1SHEETREGEXSTR)

    @staticmethod
    def to_str_list(vals: str|Self|list[str|Self]) -> list[str]:
        """
        Convenience function to take any input and return a list of
        strings, even if the input was a single instance.  The intent
        is an easy way to convert a list of A1s to strings before making
        a Google Sheets call.
        """
        if isinstance(vals, str):
            return [vals]
        elif isinstance(vals, Iterable):
            return [str(v) for v in vals]
        return [str(vals)]
    
    @staticmethod
    def to_a1_list(vals: str|Self|list[str|Self]) -> list[Self]:
        """
        Convenience funciton to turn a string or list of strings to A1 class.
        The intent is for converting from either user input or a response
        from the sheets service into easier to deal with A1 classes.
        """
        if isinstance(vals, str):
            return [GoogleSheetsA1Notation(vals)]
        elif isinstance(vals, GoogleSheetsA1Notation):
            return [vals]
        elif isinstance(vals, Iterable):
            return [v if isinstance(v, GoogleSheetsA1Notation) else GoogleSheetsA1Notation(v) for v in vals]
        return [GoogleSheetsA1Notation(str(vals))]

    def __init__(self, a1: str = ""):
        self.reset()
        if a1:
            self.set_a1(a1)

    def __str__(self) -> str:
        if self._a1:
            return self._a1
        else:
            return "<invalid>"
        
    def __repr__(self) -> str:
        return f"{str(self.__class__)}:{str(self)}"
    
    def __eq__(self, value: str) -> bool:
        """Object is equal if the A1 string matched exactly"""
        return self._a1 == value
    
    def __iadd__(self, rows: int)  -> Self:
        """Self += X means appending X rows from the end"""
        self.append_rows(rows)
        return self
    
    def __isub__(self, rows: int) -> Self:
        """Self -= X means reducing X rows from the end"""
        self.reduce_rows(rows)
        return self
    
    def __imul__(self, cols: int) -> Self:
        """Self *= X means appending X columns from the end"""
        self.append_cols(cols)
        return self
    
    def __itruediv__(self, cols: int) -> Self:
        """Self /= means reducing X columns from the end"""
        self.reduce_cols(cols)
        return self

    def valid(self) -> bool:
        """If the A1 is present its been validated"""
        return bool(self._a1)

    def __bool__(self) -> bool:
        return self.valid()
    
    def __nonzero__(self) -> bool:
        """nonzero in this context means number of cells, which really means a valid bounded range"""
        return bool(len(self))
    
    def __len__(self) -> int:
        """
        In A1 its impossible to know how many cells exist when unbounded without
        knowing actual sheet dimensions so we return 0 when unbounded, otherwise
        the number of cells in a range.
        """
        if self.bounded:
            total = self.end_row - self.start_row
            total *= (self.end_col_int - self.start_col_int) + 1
            return total
        else:
            return 0
        
    def __contains__(self, value: str|Self) -> bool:
        """
        Can we say one A1 is a superset of another?
        For example A2:B5 in A:Z is True because A2:B5 is within the A:Z range.
        """
        return self.contains(value)

    def reset(self) -> None:
        """
        Reset the state.
        Empty _a1 means invlalid.
        Empty/0 cols/rows means unbounded (assuming _a1 is valid)
        """
        self._a1 = ""
        self._sheet = ""
        self._start_col = ""
        self._end_col = ""
        self._start_col_int = 0
        self._end_col_int = 0
        self._start_row = 0
        self._end_row = 0

    @classmethod
    def col_to_int(cls, column: str) -> int:
        """
        Convert a sheet column A-ZZZ indexing to its integer equivalent.
        Note that this is 1-based, so 'A' goes to 1.
        A return value of 0 means invalid column, this is a raw A-ZZZ to int
        so unbounded is not an option here.

        column: String in A-ZZZ format to translate.

        return: Integer index translation or 0 if invalid.
        """
        c = column.upper()
        num = 0
        m = cls._a1_col_re.match(c)
        if m:
            for i, v in enumerate(reversed(list(c))):
                o = ord(v) - 64
                num += o * (26 ** i)
    
        return num
    
    @classmethod
    def int_to_col(cls, index: int) -> str:
        """
        Translate an int column index to its A1 equivalent, A-ZZZ
        Note this is 1-based and an empty string signals invalid index.
        
        index:  1-based column index

        return: String of A-ZZZ of translated index or empty string if
                invalid index.
        """
        col = ""
        i = int(index)
        if i <= GoogleSheetsMaxColumns:
            for p in [2,1,0]:
                d, r = divmod(i, 26 ** p)
                if d:
                    if d > 26:
                        leftovers = d - 26
                        col += 'Z'
                        i = r + (leftovers  * (26 ** p))
                    else:
                        col += chr(d + 64)
                        i = r
                else:
                    i = r
        return col  

    @classmethod
    def valid_a1(cls, a1: str) -> bool:
        """
        Is the supplied A1 string valid notation?
        returns: True/False if a1 is valid/invalid format.
        """
        return bool(cls._a1_re.match(a1))
    
    @classmethod
    def generate_a1(cls, sheet: str = "",
                    start_col: str|int = "", start_row: int = 0,
                    end_col:str|int="", end_row: int = 0) -> str:
        """
        Generate the A1 representation based on the input parameters.
        sheet:      Sheet title, can be empty.
        start_col:  Starting column, can be int index or alphabetical A-ZZZ.
                    If empty or 0 will signal unbounded start.
        start_row:  Starting row, as a 1-based integer index.
                    If 0 will signal an unbounded start.
        end_col:    Ending column, can be in index or alphabetical A-ZZZ.
                    If empty or 0 will signal unbounded end.
        end_row:    Ending row, as a 1-based integer index.
                    If 0 will signal an unbounded end.

        returns:    A1 string representation or empty string if invalid.
        """
        a1 = str(sheet)
        if cls._a1_sheet_re.match(a1):
            # if someone passes in a string that does not already wrap uncool chars
            # in a " or ' then we need to do it for them
            if not (a1[0] == '\'' or a1[0] == '\"'):
                if not re.match(r"^[a-zA-Z]+\w*$", a1):
                    a1 = f'\"{a1}\"'
            if start_col:
                sc = cls.int_to_col(start_col) if isinstance(start_col,int) else str(start_col)
                if cls._a1_col_re.match(sc):
                    if a1:
                        a1 += '!'
                    a1 += sc
                    if start_row:
                        sr = int(start_row)
                        if sr > 0:
                            a1 += str(sr)
                    if end_col:
                        ec = cls.int_to_col(end_col) if isinstance(end_col,int) else str(end_col)
                        if cls._a1_col_re.match(ec):
                            a1 += ':' + ec
                            if end_row:
                                er = int(end_row)
                                if er > 0:
                                    a1 += str(er)
            elif start_row:
                sr = int(start_row)
                if sr > 0:
                    if a1:
                        a1 += '!'
                    a1 += sr
                    if end_row:
                        er = int(end_row)
                        if er > 0:
                            a1 += ':' + er
        else:
            a1 = ""
        return a1
    
    @classmethod
    def extract_a1(cls, a1: str) -> tuple[str,str,str,int,int]:
        """
        Take an A1 string and extract the various aspects.
        Not all aspects may exist in various unbounded situations so it is
        definitely feasible to have some aspects empty or 0.
        If everything is 'false' (empty/0) then it is invalid.

        Note that an unbounded start row/col will be set to 1/A if there
        in a corresponding col/row.  So for example blah!1:3 will be converted
        to blah!A1:3 and blah!A:F4 will be converted to blah!A1:F4 as we know
        what the start index must be

        a1: String or object to derive string to extract.
        
        return: tuple of (title, start col, start row, end col, end row)
        """
        sheet = ""
        sc = ""
        ec = ""
        sr = 0
        er = 0
        a = str(a1)
        m = cls._a1_re.match(a)
        if m:
            if m.group('sheet'):
                sheet = m.group('sheet')
            if m.group('start_col'):
                sc = m.group('start_col')
            if m.group('start_row'):
                sr = int(m.group('start_row'))
            if m.group('end_col'):
                ec = m.group('end_col')
            if m.group('end_row'):
                er = int(m.group('end_row'))
            # unbounded starts are tricky to describe and report
            # easier to just detect them here and set the actual
            # value since they have to start at A/1 anyway
            if sr and not sc:
                sc = 'A'
            elif sc and not sr:
                sr = 1
        else:
            # easier to do a second check for just a straight unbounded sheet 
            # rather than make that main regex any more complicated
            # need to get better with look ahead/behind assertions
            pattern = cls._a1_sheet_re.pattern + '$'
            m = re.match(pattern, a)
            if m:
                sheet = m.group(0)
        return (sheet, sc, sr, ec, er)
    
    @classmethod
    def valid_dimensions(cls, dims: tuple[str,str,str,int,int]) -> bool:
        """
        Is a dimension tuple valid?
        Valid in this case means all values are empty/0 or have empty
        start with non-empty end.
        """
        title, sc, sr, ec, er = dims
        valid = True
        if not sc and not sr:
            # cant have no start row or col but and end, for that you
            # would use A: to mean 'from the beginning'
            valid = not(ec or er or not title)
        elif sc and ec:
            valid = cls.col_to_int(ec) >= cls.col_to_int(sc)
        # colums have to be increasing but not necessarily rows
        # for example A5:B2 is valid but not B2:A5
        return valid
         
    @classmethod
    def update_a1(cls, a1: str, sheet: str|None = None,
                  start_col: str|int|None = None, start_row: int|None = None,
                  end_col: str|int|None = None, end_row: int|None = None) -> str:
        """
        Update the aspects of an exsting A1 string with supplied parameters.
        A value of None for a parameter means do not update the existing value. 
        """
        s, sc, sr, ec, er = cls.extract_a1(a1)
        if sheet is not None:
            s = sheet
        if start_col is not None:
            sc = cls.int_to_col(start_col) if isinstance(start_col,int) else str(start_col)
        if end_col is not None:
            ec = cls.int_to_col(end_col) if isinstance(end_col,int) else str(end_col)
        if start_row is not None:
            sr = int(start_row)
        if end_row is not None:
            er = int(end_row)

        return cls.generate_a1(s, sc, ec, sr, er)
        
    
    def set_a1(self, a1: str) -> bool:
        """
        Set the internal state of this object to the supplied A1 string.

        return: True is successful, False if failed which would mean an invalid a1.
        """
        dims = self.extract_a1(a1)
        success = False
        if self.valid_dimensions(dims):
            sheet, sc, sr, ec, er = dims 
            self._a1 = a1
            self._sheet = sheet
            self._start_col = sc
            self._start_row = sr
            self._end_col = ec
            self._end_row = er
            self._start_col_int = self.col_to_int(sc)
            self._end_col_int = self.col_to_int(ec)
            success = True
        return success
    
    def update(self, sheet: str|None = None,
               start_col: str|int|None = None, start_row: int|None = None,
               end_col: str|int|None = None, end_row: int|None = None) -> bool:
        """
        Update existing aspects of the current A1 string.
        A value of None signals do not update that particular aspect.

        return: True if successfully updates, False otherwise which would imply invalid parameter.
        """
        s = self._sheet if sheet is None else str(sheet)
        sc = self._start_col if start_col is None else self.int_to_col(start_col) if isinstance(start_col,int) else str(start_col)
        ec = self._end_col if end_col is None else self.int_to_col(end_col) if isinstance(end_col,int) else str(end_col)
        sr = self._start_row if start_row is None else int(start_row)
        er = self._end_row if end_row is None else int(end_row)
        a1 = self.generate_a1(s, sc, sr, ec, er)
        return self.set_a1(a1) if a1 else False

    @property
    def a1(self) -> str:
        """Current A1 string, if empty the object is invalid"""
        return self._a1
    
    @a1.setter
    def a1(self, value: str) -> None:
        if not self.set_a1(value):
            raise ValueError(f"invalid A1 notation: {value}")
        
    @property
    def sheet(self) -> str:
        """Sheet title, can be empty which means sheet ID 0"""
        return self._sheet
    
    @sheet.setter
    def sheet(self, value: str) -> None:
        self.update(sheet=value)
    
    @property
    def start_col(self) -> str:
        """Start column in A-ZZZ, empty means unbounded"""
        return self._start_col
    
    @property
    def end_col(self) -> str:
        """End column in A-ZZZ, empty means unbounded"""
        return self._end_col
    
    @property
    def start_col_int(self) -> int:
        """Start column in 1-based integer index, 0 means unbounded"""
        return self._start_col_int
    
    @property
    def end_col_int(self) -> int:
        """End column in 1-based integer index, 0 means unbounded"""
        return self._end_col_int
    
    @property
    def start_row(self) -> int:
        """Start row in 1-based integer index, 0 means unbounded"""
        return self._start_row
    
    @property
    def end_row(self) -> int:
        """Start row in 1-based integer index, 0 means unbounded"""
        return self._end_row
        
    @property
    def rows_bounded(self) -> bool:
        """True if rows have bounded start/end"""
        return self._start_row and self._end_row
    
    @property
    def cols_bounded(self) -> bool:
        """True if cols have bounded start/end"""
        return self._start_col and self._end_col
    
    @property
    def bounded(self) -> bool:
        """True if both rows and cols are bounded"""
        return self.rows_bounded and self.cols_bounded
    
    @property
    def num_rows(self) -> int:
        """
        Number of rows in the A1.  This is only valid when rows
        are bounded so in an unbounded situation returns 0
        """
        return self._end_row - self._start_row if self.rows_bounded else 0
    
    @property
    def num_cols(self) -> int:
        """
        Number of cols in the A1.  This is only valid when cols
        are bounded so in an unbounded situation returns 0
        """
        return self._end_col_int - self._start_col_int if self.cols_bounded else 0
    
    @property
    def dimensions(self) -> tuple[int,int,int,int]:
        """Easy access to the coordinates as ints"""
        return (self._start_col_int, self._start_row, self._end_col_int, self._end_row)
        
    def contains(self, a1: str|Self) -> bool:
        """
        Does the supplied A1 range exist completely inside the current A1 range?
        To be 'contained' both A1s must be valid, both sheet titles are equivalent,
        and the rectangle in integer coordinates must fit inside the object coordinates.
        For this comparison an unbounded dimension is considered infinity.
        """
        contained = False
        a = a1 if isinstance(a1,GoogleSheetsA1Notation) else GoogleSheetsA1Notation(str(a1))
        if a and self._a1:
            if a.sheet == self._sheet:
                if self.bounded:
                    if a.bounded:        
                        contained = (a.start_col_int >= self._start_col_int and a.end_col_int <= self._end_col_int and 
                                    a.start_row >= self._start_row and a.end_row <= self._end_row)
                elif self.rows_bounded:
                    if a.rows_bounded:
                        contained = a.start_row >= self._start_row and a.end_row <= self._end_row
                elif self.cols_bounded:
                    if a.cols_bounded:
                        contained = a.start_col_int >= self._start_col_int and a.end_col_int <= self._end_col_int
                else:
                    # self is unbounded so therefore if 'sheet' is the same its contained
                    contained = True
        return contained
      
    def append_rows(self, rows: int ) -> bool:
        """
        Append a number of rows to the end of the current A1 range.

        rows: Number of rows to add.  This can be negative to reduce or 0 to do nothing.
        
        return: True if successful, False if not, which would be exceeding the cell limit.
        """
        if self.rows_bounded and rows:
            new_end_row = self._end_row + rows
            return self.update(end_row=new_end_row) if new_end_row > 0 else False
        return True

    
    def append_cols(self, cols: int) -> bool:
        """
        Append a number of cols to the end of the current A1 range.

        cols: Number of cols to add.  This can be negative to reduce or 0 to do nothing.
        
        return: True if successful, False if not, which would be exceeding the col limit of 'ZZZ'
        """
        if self.cols_bounded and cols:
            ec = self.col_to_int(self._end_col)
            new_end_col = ec + cols
            return self.update(end_col=new_end_col) if new_end_col > 0 and new_end_col <= GoogleSheetsMaxColumns else False
        return True

    def reduce_rows(self, rows: int) -> bool:
        """
        Reduce a number of rows from the end of the current A1 range.

        rows: Number of rows to remove.  This can be negative to append or 0 to do nothing.
        
        return: True if successful, False if not, which would be going to negative index.
        """
        return self.append_rows(-rows)

    def reduce_cols(self, cols: int) -> bool:
        """
        Reduce a number of cols from the end of the current A1 range.

        cols: Number of cols to remove.  This can be negative to append or 0 to do nothing.
        
        return: True if successful, False if not, which would be going to negative index.
        """
        return self.append_cols(-cols)

    def reshape(self, rows: int, cols: int) -> bool:
        """
        Resets row and col length, if either is 0 that dimension is unbounded
        both at zero sets to full sheet unbounded
        """
        return self.update(start_col=1, end_col=cols, start_row=1,end_row=rows) if rows >= 0 and cols >= 0 else False 
            