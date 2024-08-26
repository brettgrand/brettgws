

from .resources import Spreadsheet
from .requests import *
from .a1 import GoogleSheetsA1Notation
from .ops import *
from .sheet import GoogleSheet

from typing import Self

class GoogleSpreadSheet():

    def __init__(self, spreadsheet: Spreadsheet|dict|str = Spreadsheet()) -> None:
        self._spreadsheet = (Spreadsheet(spreadsheet) if isinstance(spreadsheet, str) else
                             spreadsheet if isinstance(spreadsheet, Spreadsheet) else
                             Spreadsheet(**dict(spreadsheet)))

    def __bool__(self) -> bool:
        return bool(self._spreadsheet)
    
    def __str__(self) -> str:
        return str(self._spreadsheet)
    
    def __repr__(self) -> str:
        return f"{self.__class__}:{str(self)}"
    
    def __len__(self) -> int:
        """
        In this context length is the number of sheets in this spreadsheet.
        Or 0 if unconnected,
        """
        return len(self._spreadsheet.sheets)
    
    def __contains__(self, val: str|int) -> bool:
        """
        Is the sheet in this spreadsheet?
        val can be either a string (title) or int (ID)
        """
        has_it = False
        if isinstance(val,int):
            for s in self._spreadsheet.sheets:
                if s.properties.sheetId == val:
                    has_it = True
                    break
        else:
            for s in self._spreadsheet.sheets:
                if s.properties.title == val:
                    has_it = True
                    break
        return has_it
    
    def __getitem__(self, item: str|int) -> GoogleSheet:
        """
        Get the sheet.  In this context if item is a
        string that is by title and if it is an int is is by index,
        index in this case meaning sheet index, not list index
        """
        if self._spreadsheet:
            if isinstance(item,int):
                for s in self._spreadsheet.sheets:
                    if s.properties.index == item:
                        return GoogleSheet(self.spreadsheet_id, s)
            else:
                for s in self._spreadsheet.sheets:
                    if s.properties.title == item:
                        return GoogleSheet(self.spreadsheet_id, s)
        raise KeyError(f"{item} not in sheets[]")
    
    @property
    def id(self) -> str:
        return self._spreadsheet.spreadsheetId
    
    @id.setter
    def spreadsheet_id(self, val: str) -> None:
        self._spreadsheet = Spreadsheet(spreadsheetId=val)
        if self.id:
            self.get()

    @property
    def spreadsheet(self) -> Spreadsheet:
        return self._spreadsheet
    
    @property
    def sheets(self) -> list[GoogleSheet]:
        return [GoogleSheet(self.spreadsheet_id, s) for s in self._spreadsheet.sheets]

    @property
    def title(self) -> str:
        if self._spreadsheet:
            return self._spreadsheet.properties.title
        else:
            return 'unconnected'
        
    def clear(self) -> None:
        self._spreadsheet = Spreadsheet()

    def get(self, ranges : list[GoogleSheetsA1Notation|str] = [],
            includeGridData: bool = False) -> Spreadsheet:
        spreadsheet = get(self.id, ranges, includeGridData)
        if spreadsheet:
            self._spreadsheet = spreadsheet
        return spreadsheet
    
    @staticmethod
    def create(spreadsheet: Spreadsheet|dict) -> Self:
        return create(spreadsheet)
    
    def batchUpdate(self, request: GoogleSheetsUpdateRequest|dict) -> GoogleSheetsUpdateRequestResponse:
        response = batchUpdate(self.id, request)
        if response:
            if ((isinstance(request, GoogleSheetsUpdateRequest) and request.includeSpreadsheetInResponse) or
                request.get("includeSpreadsheetInResponse", False)):
                self._spreadsheet = response.updatedSpreadsheet
        return response

    def clearValues(self, ranges: str|list[str|GoogleSheetsA1Notation]) -> ClearValuesRequestResponse:
        return clearValues(self.spreadsheet_id, ranges)
    
    def getValues(self, ranges: str|list[str|GoogleSheetsA1Notation],
                  dimension: str = "ROWS",
                  valueRenderOption: str = "FORMATTED",
                  dateTimeRenderOption: str = "SERIAL") -> GetValuesRequestResponse:
        return getValues(self.spreadsheet_id, ranges, dimension,
                         valueRenderOption, dateTimeRenderOption)
    
    def updateValues(self, data: ValueRange|list[ValueRange],
                 valueInputOption: str = "USER",
                 includeValuesInResponse: bool = False,
                 valueRenderOption: str = "FORMATTED",
                 dateTimeRenderOption: str = "SERIAL") -> UpdateValuesRequestResponse:
        return updateValues(self.spreadsheet_id, data, valueInputOption,
                            includeValuesInResponse, valueRenderOption, dateTimeRenderOption)
    
    # maybe someday getDataByFilter or copyTo
    
