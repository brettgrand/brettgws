

from typing import Self
from collections.abc import Iterable

from .a1 import GoogleSheetsA1Notation
from .resources import *
from .requests import GoogleSheetsUpdateRequest, GoogleSheetsUpdateRequestResponse
from .ops import *
from .requests import *

class GoogleSheet():
    """
    Class representation of a sheet.  In Google Sheets parlance a 'sheet' is
    an invidual sheet from with a parent 'spreadsheet', the different tabs on
    the spreadsheet itself.  Typcially this is what you would work with as this
    is where the data actually resides.  An actual request to a sheet would be
    addressed with spreadsheetId to the parent spreadsheet and sheetId which is
    the identifier of the sheet within that spreadsheet.  For a lot of operations
    the sheet addressing is done via the range A1.
    """
    def __init__(self, spreadsheetid: str,
                 sheet: Sheet|dict) -> None:
        self._spreadsheetid = spreadsheetid
        self._sheet = sheet if isinstance(sheet, Sheet) else Sheet(**sheet)
        self._props = self._sheet.properties
        self._update_a1()

    def _update_a1(self) -> None:
        """
        Sheet dimensions have changed, update the representative A1
        """
        self._a1 = GoogleSheetsA1Notation.generate_a1(self.title,
                                                      'A', 1,
                                                      self.cols, self.rows)

    @property
    def a1(self) -> str:
        return self._a1.a1

    @property
    def is_grid(self) -> bool:
        """
        Easy way to determine if its a GRID sheet or not,
        GRID being the usual grid of cells.
        """
        return self._props.sheetType == 'GRID'

    def __str__(self) -> str:
        return f"{str(self._props)}<{self._a1}>"
    
    def __repr__(self) -> str:
        return f"{self.__class__}:{str(self)}"
    
    def __len__(self) -> int:
        """
        Is this context length is number of cells in the sheet
        """
        return self.rows * self.cols
    
    @property
    def spreadsheet_id(self) -> str:
        return self._spreadsheetid
    
    @property
    def sheet(self) -> Sheet:
        return self._sheet

    @property
    def title(self) -> str:
        return self._props.title
    
    @property
    def index(self) -> int:
        """
        Index within the spreadsheet, which is the ordering you see
        of the tabs when you open the spreadsheet.  The index can shift
        by update, but the sheetId is always constant.
        """
        return self._props.index
    
    @property
    def sheet_id(self) -> int:
        """
        Unique ID of the sheet within the spreadsheet.  The index can
        be changed but not the sheet ID.
        """
        return self._props.sheetId

    @property
    def sheet_type(self) -> str:
        return self._props.sheetType
    
    @property
    def rows(self) -> int:
        return self._props.gridProperties.rowCount
    
    @property
    def cols(self) -> int:
        return self._props.gridProperties.columnCount
    
    @property
    def dimensions(self) -> tuple[int,int]:
        return (self.rows, self.cols)
    
    def batchUpdate(self, request: GoogleSheetsUpdateRequest|dict) -> GoogleSheetsUpdateRequestResponse:
        """
        Convenience method to update a sheet and will fill in the corresponding sheet
        and spreadsheet IDs so the caller doens't have to.
        """
        response = batchUpdate(self._spreadsheetid, request)
        if response:
            if ((isinstance(request, GoogleSheetsUpdateRequest) and request.includeSpreadsheetInResponse) or
                request.get("includeSpreadsheetInResponse", True)):
                ss = response.updatedSpreadsheet
                if not ss:
                    raise RuntimeError("Spreadsheet should have been included in response but isnt?")
                found_it = False
                for s in ss.sheets:
                    if s.properties.sheetId == self.sheet_id:
                        self._props = s.properties
                        self._update_a1()
                        found_it = True
                if not found_it:
                    raise RuntimeError(f"This sheet: {self.title}/{self.sheet_id} should be available?")
        return response
    
    def updateRequests(self):
        """
        Start a batchUpdate() chain, makes it easy to append operations to pack
        into a request before sending it.
        """
        chain = _SheetUpdateChain(self)
        return chain

    def clearValues(self, ranges: str|list[str|GoogleSheetsA1Notation]) -> ClearValuesRequestResponse:
        """
        Set a range of cells in a seet to empty or blank
        In the sheet context, need to confirm ranges are valid and
        have the correct sheet
        https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchClear
        """
        a1list = GoogleSheetsA1Notation.to_a1_list(ranges)
        for a1 in a1list:
            if not a1:
                raise ValueError("Invalid range value detected")
            if not a1.sheet:
                a1.sheet = self.title
            elif a1.sheet != self.title:
                raise ValueError("Cannot clear ranges from other sheets")
        return clearValues(self.spreadsheet_id, a1list)
    
    def getValues(self, ranges: str|list[str|GoogleSheetsA1Notation],
                  dimension: str = "ROWS",
                  valueRenderOption: str = "FORMATTED",
                  dateTimeRenderOption: str = "SERIAL") -> GetValuesRequestResponse:
        """
        Get the specified range of values.  Empty blocks will not be returned.
        For example if A1:C5 is requested but only A1,A2 have any data then a
        list of length 2 will be returned.
        In the sheet context, need to confirm ranges are valid and
        have the correct sheet
        https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchGet
        """
        a1list = GoogleSheetsA1Notation.to_a1_list(ranges)
        for a1 in a1list:
            if not a1:
                raise ValueError("Invalid range value detected")
            if not a1.sheet:
                a1.sheet = self.title
            elif a1.sheet != self.title:
                raise ValueError("Cannot get ranges from other sheets")
        return getValues(self.spreadsheet_id, a1list, dimension,
                         valueRenderOption, dateTimeRenderOption)
    
    def updateValues(self, data: ValueRange|list[ValueRange],
                 valueInputOption: str = "USER",
                 includeValuesInResponse: bool = False,
                 valueRenderOption: str = "FORMATTED",
                 dateTimeRenderOption: str = "SERIAL") -> UpdateValuesRequestResponse:
        """
        Write specified values to the sheet.
        https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdate
        """
        dlist = data if isinstance(data, Iterable) else [data]
        for d in dlist:
            a1 = GoogleSheetsA1Notation(d.range)
            if not a1:
                raise ValueError("Invalid range value detected")
            if not a1.sheet:
                a1.sheet = self.title
            elif a1.sheet != self.title:
                raise ValueError("Cannot get ranges from other sheets")
            d.range = a1.a1
        return updateValues(self.spreadsheet_id, dlist, valueInputOption,
                            includeValuesInResponse, valueRenderOption, dateTimeRenderOption)

class _SheetUpdateChain():
    """
    Utility class for building up a chaing of update requests.
    The spreadsheet batchUpdate method can take a list of requests at once
    and it is more efficient to provide a number of them at once rather than
    request/response/request/response/etc.  So this provides a means to add
    a chain of requests and then terminate with execut().
    The idea is you would:
    response = sheet.updateRequests().request1(params).request2(params).execute()
    Where there can be any requestN(params)
    """
    def __init__(self, sheet: GoogleSheet) -> None:
        if not sheet:
            raise ValueError("Must be a valid sheet for an update operation")
        self._sheet = sheet
        self._requests = []
        self._need_sheet_update = False

    def execute(self, includeSpreadsheetInResponse: bool = False,
                responseRanges: List[str] = [],
                responseIncludeGridData: bool = False):
        """
        Terminate a request chain and send the actual batchUpdate
        """
        if self._requests:
            requests = [r.to_request() for r in self._requests]
            request = GoogleSheetsUpdateRequest(requests, includeSpreadsheetInResponse or self._need_sheet_update,
                                                responseRanges, responseIncludeGridData)
            return self._sheet.batchUpdate(request)
        return GoogleSheetsUpdateRequestResponse(self._sheet.spreadsheet_id)
    
    def appendDimension(self, num: int, dimension: str = "ROWS") -> Self:
        """
        Append rows or columns to the end.
        https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#appenddimensionrequest
        """
        if num > 0:
            dim = GoogleSheetsEnum.dimension(dimension)
            if not dim:
                raise ValueError("appendDimension() dimension parameter must be \'ROWS\' or \'COLS' not: " + dimension)
            self._requests.append(AppendDimensionRequest(self._sheet.sheet_id, dim, num))
            self._need_sheet_update = True
        elif num < 0:
            raise ValueError("appendDimension(): num parameter must be >= 0")
        return self
    
    def reduceDimension(self, num: int, dimension: str = "ROWS") -> Self:
        """
        Remove specified number of rows or columns from the end.
        There is no corresponding GWS request for this, this is a convenience
        to add logic around deleteDimension
        """
        "reduce rows or cols from end"
        if num > 0:
            dim = GoogleSheetsEnum.dimension(dimension)
            if not dim:
                raise ValueError("reduceDimension() dimension parameter must be \'ROWS\' or \'COLS' not: " + dimension) 
            start = self._sheet.rows - num if dim == "ROWS" else self._sheet.cols - num
            if start < 0:
                raise ValueError("reduceDimension() cannot reduce past 0")
            return self.deleteDimension(start, -1, dim)

        return self
    
    def deleteDimension(self, start: int, end: int, dimension: str = "ROW") -> Self:
        """
        Remove rows or columns from the specified range.
        https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#deletedimensionrequest
        """
        if start >= 0:
            dim = GoogleSheetsEnum.dimension(dimension)
            if not dim:
                raise ValueError("deleteDimension() parameter must be \'ROWS\' or \'COLS' not: " + dimension) 
            request = DeleteDimensionRequest(self._sheet.sheet_id, dim,
                                             start, None)
            if end > 0:
                # not specifying means 'to the end', as in: delete from start to the end
                # leaving [0 - (start -1)]
                request.range.endIndex = end
            self._requests.append(request)
            self._need_sheet_update = True
        return self
    
    def expandDimensions(self, rows:int, cols:int) -> Self:
        """
        Convenience method wrapping up both append rows and cols.
        """
        return self.appendDimension(rows, "ROWS").appendDimension(cols, "COLS")
    
    def setDimensions(self, num: int, dimension: str = "ROWS") -> Self:
        """
        Hard set to specified number of rows/cols
        """
        dim = GoogleSheetsEnum.dimension(dimension)
        if not dim:
            raise ValueError("deleteDimension() parameter must be \'ROWS\' or \'COLS' not: " + dimension)
        elif dim == 'ROWS':
            if num > self._sheet.rows:
                return self.appendDimension(num - self._sheet.rows, dim)
            elif num < self._sheet.rows:
                return self.deleteDimension(num, -1, dim)
        else:
            if num > self._sheet.cols:
                return self.appendDimension(num - self._sheet.cols, dim)
            elif num < self._sheet.cols:
                return self.deleteDimension(num, -1, dim)
        return self
             
    def reshapeDimensions(self, rows: int, cols: int) -> Self:
        """hard reset of the dimensions from supplied range"""
        return self.setDimensions(rows, "ROWS").setDimensions(cols, "COLS")
    
    def insertDimension(self, index: int, num: int,
                        dimension: str = "ROWS",
                        inheritFromBefore: bool = True) -> Self:
        """
        Insert number of rows/cols from the specified index.
        inheritFromBefore is to either inherit from prior row/col (index-1) at True
        or from following row/col (index + row) at False
        https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#insertdimensionrequest
        """
        if num > 0:
            dim = GoogleSheetsEnum.dimension(dimension)
            if not dim:
                raise ValueError("insertDimension() dimension parameter must be \'ROWS\' or \'COLS' not: " + dimension)
            elif dim == "ROWS" and index > self._sheet.rows:
                raise ValueError("insertDimension(), row start index out of range")
            elif index > self._sheet.cols:
                raise ValueError("insertDimension(), col start index out of range")
            
            request = InsertDimensionRequst(self._sheet.sheet_id, dim,
                                            index, index + num, inheritFromBefore)
            self._requests.append(request)
            self._need_sheet_update = True
        return self

