
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from .resources import *
from .requests import *
from .a1 import GoogleSheetsA1Notation

from functools import partial

from ..access import gws

# do this as module level or a parent class instance?
# simpler at module level and achieves the same thing
_get_service = partial(gws.get_service, "sheets", "v4")

def get(spreadsheetid: str,
        ranges : list[GoogleSheetsA1Notation|str] = [],
        includeGridData: bool = False) -> Spreadsheet:
    """
    Wrapper for calling the get() spreadsheet method.
    See https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/get
    This is for retrieving spreadsheet properties but can also include data
    if you need it.
    The decorators will handle requires scopes and building the service.
    """
    ret = Spreadsheet()
    if spreadsheetid:
        range = [str(r) for r in ranges]
        response = _get_service().spreadsheets().get(spreadsheetId=spreadsheetid,
                                                     ranges=range,
                                                     includeGridData=includeGridData).execute()
        if response:
            ret = Spreadsheet(**response)
    return ret

def create(spreadsheet: Spreadsheet|dict|str) -> Spreadsheet:
    """
    Wrapper for calling the create() spreadsheet method.
    See https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/create
    This is for creating a whole new spreadsheet instance, not a sheet within a
    spreadsheet.
    The decorators will handle requires scopes and building the service.
    """
    body = spreadsheet.to_base() if isinstance(spreadsheet,Spreadsheet) else asdict(spreadsheet) if is_dataclass(spreadsheet) else spreadsheet
    response = _get_service().spreadsheets().create(body=body).execute()
    if response:
        return Spreadsheet(**response)
    return Spreadsheet()

def batchUpdate(spreadsheetid: str, request: GoogleSheetsUpdateRequest|dict):
    """
    Wrapper for calling the batchUpdate() spreadsheet method.
    See https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/batchUpdate
    This is for altering any spreadsheet properties but not actual data read/write/clear
    which is done from the values() resource.
    The decorators will handle requires scopes and building the service.
    """
    body = request.to_base() if isinstance(request, GoogleSheetsUpdateRequest) else asdict(request) if is_dataclass(request) else request
    response = _get_service().spreadsheets().batchUpdate(spreadsheetId=spreadsheetid, body=body).execute()
    if response:
        return GoogleSheetsUpdateRequestResponse(**response)
    return GoogleSheetsUpdateRequestResponse()
    
    # maybe someday getDataByFilter or copyTo

def clearValues(spreadsheetId: str,
                ranges: str|list[str|GoogleSheetsA1Notation]) -> ClearValuesRequestResponse:
    """
    Wrapper for calling the clear() method on the values resource.
    See https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/clear
    Setting the specified range of cells to the empty or blank state.
    The decorators will handle requires scopes and building the service.
    """
    values = _get_service().spreadsheets().values()
    response = ClearValuesRequestResponse(spreadsheetId)
    range_list = GoogleSheetsA1Notation.to_str_list(ranges)
    if len(range_list) > 0:
        body = {"ranges": range_list}
        r = values.batchClear(spreadsheetId=spreadsheetId, body=body).execute()
        if r:
            response.spreadsheetId = r.get('spreadsheetId', "")
            response.clearedRanges = GoogleSheetsA1Notation.to_a1_list(r.get('clearedRanges', []))
        else:
            response.spreadsheetId = ""
    return response

def getValues(spreadsheetId: str,
              ranges: str|list[str|GoogleSheetsA1Notation],
              dimension: str = "ROWS",
              valueRenderOption: str = "FORMATTED",
              dateTimeRenderOption: str = "SERIAL") -> GetValuesRequestResponse:
    """
    Wrapper for calling the batchGet() method on the values resource.
    See https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchGet
    Get the cell data from the specified ranges.  We always call batchGet, even for
    a single range instead of calling get() just for consistency.  Calling batchGet()
    with only 1 range is fine.
    The decorators will handle requires scopes and building the service.
    """
    values = _get_service().spreadsheets().values()
    response = GetValuesRequestResponse(spreadsheetId)
    range_list = GoogleSheetsA1Notation.to_str_list(ranges)
    dim = GoogleSheetsEnum.dimension(dimension)
    if not dim:
        raise ValueError(f"Invalid majorDimension value: {dimension}")
    value_render = GoogleSheetsEnum.valueRenderOption(valueRenderOption)
    if not value_render:
        raise ValueError(f"Invalid valueRenderOption value: {valueRenderOption}")
    date_time_render = GoogleSheetsEnum.dateTimeRenderOption(dateTimeRenderOption)
    if not date_time_render and value_render != "FORMATTED_VALUE":
        raise ValueError(f"Invalid dateTimeRenderOption value: {dateTimeRenderOption}")

    if len(range_list) > 0:
        r = values.batchGet(spreadsheetId=spreadsheetId,
                            ranges=range_list,
                            majorDimension=dim,
                            valueRenderOption=value_render,
                            dateTimeRenderOption=date_time_render).execute()
        if r:
            response.spreadsheetId = r.get('spreadsheetId', "")
            response.valueRanges = [ValueRange(**vr) for vr in r.get("valueRanges",{})]
        else:
            response.spreadsheetId = ""
    return response

def updateValues(spreadsheetId: str,
                 data: ValueRange|list[ValueRange],
                 valueInputOption: str = "USER",
                 includeValuesInResponse: bool = False,
                 valueRenderOption: str = "FORMATTED",
                 dateTimeRenderOption: str = "SERIAL") -> UpdateValuesRequestResponse:
    """
    Wrapper for calling the batchUpdate() method on the values resource.
    See https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdate
    Write the cell data to the specified ranges.  We always call batchUpdate, even for
    a single range instead of calling update() just for consistency.  Calling batchUpdate()
    with only 1 range is fine.
    The decorators will handle requires scopes and building the service.
    """
    dlist = [d.to_base() for d in data] if isinstance(data, Iterable) else [data.to_base()]
    value_input = GoogleSheetsEnum.valueInputOption(valueInputOption)
    if not value_input:
        raise ValueError(f"Invalid valueInputOption value: {valueInputOption}")
    value_render = GoogleSheetsEnum.valueRenderOption(valueRenderOption)
    if not value_render:
        raise ValueError(f"Invalid valueRenderOption value: {valueRenderOption}")
    date_time_render = GoogleSheetsEnum.dateTimeRenderOption(dateTimeRenderOption)
    if not date_time_render and value_render != "FORMATTED_VALUE":
        raise ValueError(f"Invalid dateTimeRenderOption value: {dateTimeRenderOption}")
    values = _get_service().spreadsheets().values()
    response = UpdateValuesRequestResponse(spreadsheetId)
    if len(dlist) > 0:
        body = {
            "valueInputOption": value_input,
            "data": dlist,
            "includeValuesInResponse": includeValuesInResponse,
            "responseValueRenderOption": value_render,
            "responseDateTimeRenderOption": date_time_render
        }
        r = values.batchUpdate(spreadsheetId=spreadsheetId, body=body).execute()
        if r:
            response = UpdateValuesRequestResponse(**r)
        else:
            response.spreadsheetId = ""
    return response

    
