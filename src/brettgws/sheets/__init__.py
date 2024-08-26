"""
Classes to facilitate working with Google Sheets
"""

# can address up to 'ZZZ'
GoogleSheetsMaxColumns = 18278
# current cell limit in a single GSheet
# this can be any R and C dimensions as long as RxC <= 10000000
# the row limit is anywhere between 1-10000000 depending on the number of columns
GoogleSheetsMaxCells = 10000000
