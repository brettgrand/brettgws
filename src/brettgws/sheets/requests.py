from dataclasses import dataclass, asdict, field
from typing import List
import re

from ..resources import GoogleWorkSpaceResourceBase
from .resources import *
from .a1 import GoogleSheetsA1Notation

class GoogleSheetsUpdateRequestBase(GoogleWorkSpaceResourceBase):
    """
    Base class for sheet batchUpdate requests to get the actua
    request dict into the right format.
    """
    def to_request(self) -> dict[str,dict]:
        name = self.__class__.__name__
        # need to strip off the trailing 'Request' class name and
        # set the first letter to lower case.  could be done
        # several ways but lets go re
        request = {}
        m = re.match("^([a-zA-Z])([a-zA-Z]+)Request$", name)
        if m:
            key = m.group(1).lower() + m.group(2)
            val = asdict(self)
            request[key] = val
        else:
            raise RuntimeError("Invalid Google Sheets request format for class name")

        return request

# need to add request here and pull the name out via self.__class__.__name__


@dataclass
class AppendDimensionRequest(GoogleSheetsUpdateRequestBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#appenddimensionrequest
    """
    sheetId: int
    dimension: str
    length: int

@dataclass
class DeleteDimensionRequest(GoogleSheetsUpdateRequestBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#deletedimensionrequest
    The 'range' indirection makes this a bit complicated, we want the DimensionRange
    initializer but park it in the range object.
    """
    range: DimensionRange = field(init=False)

    def __init__(self, sheetId: int, dimension: str,
                 startIndex: int|None = None,
                 endIndex: int|None = None) -> None:
        self.range = DimensionRange(sheetId, dimension, startIndex, endIndex)

    def to_base(self) -> dict:
        b = {}
        if self.range:
            b['range'] = self.range.to_base()
        return b

@dataclass
class InsertDimensionRequst(GoogleSheetsUpdateRequestBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#insertdimensionrequest
    The 'range' indirection makes this a bit complicated, we want the DimensionRange
    initializer but park it in the range object.
    """
    range: DimensionRange = field(init=False)
    inheritFromBefore: bool = field(default=True)

    def __init__(self, sheetId: int, dimension: str,
                 startIndex: int, endIndex: int,
                 inheritFromBefore: bool = True) -> None:
        self.range = DimensionRange(sheetId, dimension, startIndex, endIndex)
        self.inheritFromBefore = inheritFromBefore

    def to_base(self) -> dict:
        b = {'range': self.range.to_base(), 'inheritFromBefore': self.inheritFromBefore }
        return b

@dataclass
class GoogleSheetsUpdateRequest(GoogleSheetsUpdateRequestBase):
    """
    Generate a GSheet Batch Update request body.
    Most likely you'd use make_request() directly to generate
    the request dict JIT
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/batchUpdate#request-body
    """
    requests: List[GoogleSheetsUpdateRequestBase|dict]
    includeSpreadsheetInResponse: bool = field(default=False)
    responseRanges: List[str] = field(default_factory=list)
    responseIncludeGridData: bool = field(default=False)

def make_request(requests: list[GoogleSheetsUpdateRequestBase|dict],
                 includeSpreadsheetInResponse = False,
                 responseRanges: list[str] = [],
                 responseIncludeGridData: bool = False):
    """
    Convenience function to assemble the request with the usual parameters.
    """
    return asdict(GoogleSheetsUpdateRequest(requests=requests,
                                            includeSpreadsheetInResponse=includeSpreadsheetInResponse,
                                            responseRanges=responseRanges,
                                            responseIncludeGridData=responseIncludeGridData))


@dataclass
class GoogleSheetsUpdateRequestResponse(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/batchUpdate#response-body
    """
    spreadsheetId: str = field(default="")
    replies: List[dict] = field(default=list)
    updatedSpreadsheet: Spreadsheet|dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.fixup()

    def __bool__(self) -> bool:
        return bool(self.spreadsheetId)
    
    def fixup(self) -> None:
        self.updatedSpreadsheet = self.updatedSpreadsheet if isinstance(self.updatedSpreadsheet,Spreadsheet) else Spreadsheet(**dict(self.updatedSpreadsheet))

    def to_base(self) -> dict:
        self.fixup()
        b = asdict(self)
        b['updatedSpreadsheet'] = self.updatedSpreadsheet.to_base()
        return b

class GoogleSheetsValueRequestBase(GoogleWorkSpaceResourceBase):
    """Common base class for sheets values requests so we can filter them"""
    pass

class GoogleSheetsValueRequestResponseBase(GoogleWorkSpaceResourceBase):
    """Common base class for sheets values responses so we can filter tem"""
    pass

@dataclass
class ClearValuesRequestResponse(GoogleSheetsValueRequestResponseBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchClear#response-body
    """
    spreadsheetId: str = field(default="")
    clearedRanges: list[GoogleSheetsA1Notation|str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.fixup()

    def __bool__(self) -> bool:
        return bool(self.spreadsheetId)
    
    def fixup(self) -> None:
        self.clearedRanges = [a1 if isinstance(a1,GoogleSheetsA1Notation) else GoogleSheetsA1Notation(str(a1)) for a1 in list(self.clearedRanges)]

    def to_base(self) -> dict:
        self.fixup()
        b = {'spreadsheetId': self.spreadsheetId, 'clearedRanges': [str(a1 for a1 in self.clearedRanges)]}
        return b
    
@dataclass
class GetValuesRequestResponse(GoogleSheetsValueRequestResponseBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchGet#response-body
    """
    spreadsheetId: str = field(default="")
    valueRanges: list[ValueRange|dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.fixup()

    def __bool__(self) -> bool:
        return bool(self.spreadsheetId)
    
    def fixup(self) -> None:
        self.valueRanges = [vr if isinstance(vr,ValueRange) else ValueRange(**dict(vr)) for vr in self.valueRanges]

    def to_base(self) -> dict:
        self.fixup()
        b = {'spreadsheetId': self.spreadsheetId, 'valueRanges': [vr.to_base() for vr in self.valueRanges]}
        return b

@dataclass
class UpdateValuesRequestResponse(GoogleSheetsValueRequestResponseBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdate#response-body
    """
    spreadsheetId: str = field(default="")
    totalUpdatedRows: int = field(default=0)
    totalUpdatedColumns: int = field(default=0)
    totalUpdatedCells: int = field(default=0)
    totalUpdatedSheets: int = field(default=0)
    responses: list[UpdateValuesResponse|dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.fixup()

    def __bool__(self) -> bool:
        """Response is valid if an ID came back"""
        return bool(self.spreadsheetId)
    
    def fixup(self) -> None:
        self.responses = [r if isinstance(r,UpdateValuesResponse) else UpdateValuesResponse(**dict(r)) for r in self.responses]

    def to_base(self) -> dict:
        self.fixup()
        b = asdict(self)
        b['responses'] = [r.to_base() for r in self.responses]
        return b
    





    