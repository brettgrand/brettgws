
import pytest

from brettgws.sheets.a1 import GoogleSheetsA1Notation

def test_valid_bounded():
    a1 = GoogleSheetsA1Notation("test!C4:BX2")
    assert(a1)
    assert(a1.sheet == "test")
    assert(a1.start_col == 'C')
    assert(a1.end_col == 'BX')
    assert(a1.start_row == 4)
    assert(a1.end_row == 2)
    assert(a1.start_col_int == 3)
    assert(a1.end_col_int == 76)

def test_unbounded():
    a1 = GoogleSheetsA1Notation("test!4:ASC")
    assert(a1)
    assert(a1.start_col == 'A')
    assert(a1.start_row == 4)
    assert(a1.end_col == 'ASC')
    assert(a1.end_row == 0)

def test_valid_titles():
    a1 = GoogleSheetsA1Notation("test")
    assert(a1)
    assert(a1.sheet == "test")
    assert(a1.start_col == "")
    assert(a1.start_row == 0)
    assert(a1.end_col == "")
    assert(a1.end_row == 0)

    title_with_spaces = "this is a test"
    a1.sheet = title_with_spaces
    assert(a1.sheet == '\"' + title_with_spaces + '\"')

def test_invalid():
    a1 = GoogleSheetsA1Notation()
    assert(not a1)
    a1 = GoogleSheetsA1Notation("test!:d3")
    assert(not a1)
    a1 = GoogleSheetsA1Notation("test:")
    assert(not a1)
    a1 = GoogleSheetsA1Notation("test!F2:A3")
    assert(not a1)

def test_specials():
    a1 = GoogleSheetsA1Notation("test!C4:AB25")
    a1 += 2
    assert(a1.a1 == "test!C4:AB27")
    assert(a1.end_row == 27)
    a1 -=5
    assert(a1.a1 == "test!C4:AB22")
    assert(a1.end_row == 22)
    a1 *= 10
    assert(a1.a1 == "test!C4:AL22")
    assert(a1.end_col == 'AL')
    assert(a1.end_col_int == 38)
    a1 /= 18
    assert(a1.a1 == "test!C4:T22")
    assert(a1.end_col == 'T')
    assert(a1.end_col_int == 20)

    assert(len(a1) == 324)

    a1 = GoogleSheetsA1Notation('test!B:Z')
    assert(len(a1) == 0)
    a1 = GoogleSheetsA1Notation('test')
    assert(len(a1) == 0)
    a1 = GoogleSheetsA1Notation('test!6:10')
    assert(len(a1) == 0)
    a1 = GoogleSheetsA1Notation('test!6:A8')
    assert(len(a1) == 2)
    
    a1 = GoogleSheetsA1Notation('test!C4:AL22')
    compare = GoogleSheetsA1Notation("test!E7:Z22")
    assert(compare in a1)

    compare.sheet = "other"
    assert(compare not in a1)

    # confirm trying to update past the end col fails
    assert (not compare.update('test', start_col='BC'))

    compare.update('test', start_col='BC', end_col='ZZ')
    assert(compare not in a1)

    compare.update(start_col='C',start_row=4,end_col='AL',end_row=22)
    assert(a1 == compare)

