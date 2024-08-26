"""
Class implementations of sheets request resources.
As these are just logical groupings of data fields we use dataclasses
to implement.  The nested aspect does cause some headaches as there
is a handy dataclass.asdict() method to get a dict translation of the
class fields, which is exactly what that request client needs, but
there's no inverse support, as in initializing a dataclass from a dict.
So for dataclasses with dataclasses as fields we need to do a distinct
__init__ which is a bit annoying.
Not all resources/requests/responses are implemented.
"""
from dataclasses import dataclass, field, asdict
from typing import List,ClassVar

from ..resources import GoogleWorkSpaceResourceBase

class GoogleSheetsEnum():
    """
    An 'enum' in the sheets client is just a string so this is
    just to translate and validate input.
    """
    _VALID_VALUE_RENDER_OPTIONS = {
        "FORMATTED": "FORMATTED_VALUE",
        "FORMATTED_VALUE": "FORMATTED_VALUE",
        "UNFORMATTED": "UNFORMATTED_VALUE",
        "UNFORMATTED_VALUE": "UNFORMATTED_VALUE",
        "FORMULA": "FORMAULA"
    }
    _VALID_DATE_TIME_RENDER_OPTIONS = {
        "SERIAL": "SERIAL_NUMBER",
        "SERIAL_NUMBER": "SERIAL_NUMBER",
        "FORMATTED": "FORMATTED_STRING",
        "FORMATTED_STRING": "FORMATTED_STRING"
    }
    _VALID_DIMENSION_OPTIONS = {
        "ROWS": "ROWS",
        "R": "ROWS",
        "C": "COLUMNS",
        "COLS": "COLUMNS",
        "COLUMNS": "COLUMNS"
    }
    _VALID_VALUE_INPUT_OPTIONS = {
        "RAW": "RAW",
        "USER": "USER_ENTERED",
        "USER_ENTERED": "USER_ENTERED"
    }
    @classmethod
    def valueRenderOption(cls, option: str) -> str:
        """https://developers.google.com/sheets/api/reference/rest/v4/ValueRenderOption"""
        return cls._VALID_VALUE_RENDER_OPTIONS.get(str(option).upper(), "")
    
    @classmethod
    def dateTimeRenderOption(cls, option: str) -> str:
        """https://developers.google.com/sheets/api/reference/rest/v4/DateTimeRenderOption"""
        return cls._VALID_DATE_TIME_RENDER_OPTIONS.get(str(option).upper(), "")
    
    @classmethod
    def dimension(cls, dim: str) -> str:
        """https://developers.google.com/sheets/api/reference/rest/v4/Dimension"""
        return cls._VALID_DIMENSION_OPTIONS.get(str(dim), "")
    
    @classmethod
    def valueInputOption(cls, option: str) -> str:
        """https://developers.google.com/sheets/api/reference/rest/v4/ValueInputOption"""
        return cls._VALID_VALUE_INPUT_OPTIONS.get(str(option).upper(), "")

@dataclass
class NumberFormat(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#numberformat
    """
    type: str = field(default="")
    pattern: str = field(default="")

    valid_values: ClassVar[str] = ['TEXT', 'NUMBER', 'PERCENT',
                                   'CURRENCY', 'DATE', 'TIME',
                                   'DATE_TIME', 'SCIENTIFIC']

    def __post_init__(self):
        self.fixup()

    def __bool__(self) -> bool:
        return bool(self.type) and self.type in self.valid_values
    
    def fixup(self) -> None:
        if self.type:
            self.type = self.type if isinstance(self.type,str) else str(self.type)
            if self.type not in self.valid_values:
                t = str(self.type).upper()
                if t in self.valid_values:
                    self.type = t
                else:
                    raise ValueError('Invalid number format type: ' + t)

@dataclass
class Color(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#color
    """
    red: int|float = field(default=0)
    green: int|float = field(default=0)
    blue: int|float = field(default=0)
    alpha: int|float = field(default=0)

@dataclass
class SpreadsheetProperties(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets#SpreadsheetProperties
    """
    title: str = field(default="")
    locale: str = field(default="")
    autoRecalc: str = field(default="")
    timeZone: str = field(default="")
    defaultFormat: dict = field(default_factory=dict)
    iterativeCalculationSettings: dict = field(default_factory=dict)
    spreadsheetTheme: dict = field(default_factory=dict)
    importFunctionsExternalUrlAccessAllowed: bool = field(default=False)

    def __bool__(self) -> bool:
        return bool(self.title)

@dataclass
class GridProperties(GoogleWorkSpaceResourceBase):
    """https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#gridproperties"""
    rowCount: int = field(default=-1)
    columnCount: int = field(default=-1)
    frozenRowCount: int = field(default=0)
    frozenColumnCount: int = field(default=0)
    hideGridlines: bool = field(default=False)
    rowGroupControlAfter: bool = field(default=False)
    columnGroupControlAfter: bool = field(default=False)

    def __bool__(self) -> bool:
        return self.rowCount >= 0 and self.columnCount >= 0

@dataclass
class SheetProperties(GoogleWorkSpaceResourceBase):
    """https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#sheetproperties"""
    sheetId: int = field(default=-1)
    title: str = field(default="")
    index: int = field(default=-1)
    sheetType: str = field(default="")
    gridProperties: GridProperties|dict = field(default_factory=dict)
    hidden: bool = field(default=False)
    tabColor: dict = field(default_factory=dict)
    tabColorStyle: dict = field(default_factory=dict)
    rightToLeft: bool = field(default=False)
    dataSourceSheetProperties: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.fixup()

    def fixup(self) -> None:
        self.gridProperties = self.gridProperties if isinstance(self.gridProperties,GridProperties) else GridProperties(**dict(self.gridProperties))

    def to_base(self) -> dict:
        self.fixup()
        b = asdict(self)
        b['gridProperties'] = self.gridProperties.to_base()
        return b

    def __bool__(self) -> bool:
        """
        True if it is valid, which is the ID and index are 0 or positive
        as negative index is not possible
        """
        return self.sheetId >= 0 and self.index >= 0 and bool(self.sheetType) and bool(self.title)
    
    def __str__(self) -> str:
        val = ""
        if self:
            val = f"{str(self.title)}({str(self.sheetId)}[{str(self.index)}]):{str(self.sheetType)}"
            if self.is_grid():
                val += f"({self.gridProperties.rowCount}Rx{self.gridProperties.columnCount}C)"
        else:
            val = "<invalid sheet>"
        return val
    
    def is_grid(self) -> bool:
        """
        A GRID sheet is the traditional range of cells and is normally
        what you want to work with.
        """
        return self.sheetType == 'GRID'

@dataclass
class GridData(GoogleWorkSpaceResourceBase):
    """https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#griddata"""
    startRow: int = field(default=-1)
    startColumn: int = field(default=-1)
    rowData: List[dict] = field(default_factory=list)
    rowMetadata: List[dict] = field(default_factory=list)
    columnMetadata: List[dict] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.startRow >= 0 and self.startColumn >= 0

@dataclass
class GridRange(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#gridrange
    """
    sheetId: int = field(default=-1)
    startRowIndex: int|None = field(default=None)
    endRowIndex: int|None = field(default=None)
    startColunmnIndex: int|None = field(default=None)
    endColumnIndex: int|None = field(default=None)

    def __bool__(self) -> bool:
        return self.sheetId >= 0
    
@dataclass
class DimensionRange(GoogleWorkSpaceResourceBase):
    """https://developers.google.com/sheets/api/reference/rest/v4/DimensionRange"""
    sheetId: int = field(default=-1)
    dimension: str = field(default="")
    startIndex: int|None = field(default=None)
    endIndex: int|None = field(default=None)

    def __post_init__(self) -> None:
        self.fixup()

    def fixup(self) -> None:
        if self.dimension:
            d = str(self.dimension)
            self.dimension = GoogleSheetsEnum.dimension(d)
            if not self.dimension:
                raise ValueError(f"Invalid dimension value: {d}")
            
    def __bool__(self) -> bool:
        return self.sheetId >= 0 and self.dimension

@dataclass
class ValueRange(GoogleWorkSpaceResourceBase):
    """https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values#resource:-valuerange"""
    range: str = field(default="")
    majorDimension: str = field(default="")
    values: list[bool|str|float|None] = field(default_factory=list)

    def __post_init__(self):
        self.fixup()

    def fixup(self) -> None:
        if self.majorDimension:
            self.majorDimension = GoogleSheetsEnum.dimension(str(self.majorDimension))

    def __bool__(self) -> bool:
        """
        A ValueRange is valid if the range string is not empty
        and the majorDimension has a valid value.
        """
        return bool(self.range) and bool(self.majorDimension)
    
@dataclass
class UpdateValuesResponse(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/UpdateValuesResponse
    """
    spreadsheetId: str = field(default="")
    updatedRange: str = field(default="")
    updatedRows: int = field(default=0)
    updatedColumns: int = field(default=0)
    updatedCells: int = field(default=0)
    updatedData: ValueRange|dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.fixup()

    def fixup(self) -> None:
        self.updatedData = self.updatedData if isinstance(self.updatedData,ValueRange) else ValueRange(**dict(self.updatedData))

    def __bool__(self) -> bool:
        return bool(self.spreadsheetId) and bool(self.updatedRange)

    def to_base(self) -> dict:
        self.fixup()
        b = asdict(self)
        b['updatedData'] = self.updatedData.to_base()
        return b

@dataclass
class Sheet(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#sheet
    Representation of a sheet within a spreadsheet
    """
    properties: SheetProperties|dict = field(default_factory=dict)
    data: List[GridData|dict] = field(default_factory=list)
    merges: List[GridRange|dict] = field(default_factory=list)
    conditionalFormats: List[dict] = field(default_factory=list)
    filterViews: List[dict] = field(default_factory=list)
    protectedRanges: List[dict] = field(default_factory=list)
    basicFilter: List[dict] = field(default_factory=list)
    charts: List[dict] = field(default_factory=list)
    bandedRanges: List[dict] = field(default_factory=list)
    developerMetadata: List[dict] = field(default_factory=list)
    rowGroups: List[dict] = field(default_factory=list)
    columnGroups: List[dict] = field(default_factory=list)
    slicers: List[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.fixup()

    def fixup(self) -> None:
        self.properties = self.properties if isinstance(self.properties,SheetProperties) else SheetProperties(**dict(self.properties))
        self.data = [gd if isinstance(gd,GridData) else GridData(**dict(gd)) for gd in self.data]
        self.merges = [gr if isinstance(gr,GridRange) else GridRange(**dict(gr)) for gr in self.merges]

    def to_base(self) -> dict:
        self.fixup()
        b = asdict(self)
        b['properties'] = self.properties.to_base()
        b['data'] = [d.to_base() for d in self.data]
        b['merges'] = [m.to_base() for m in self.merges]
        return b

    def __bool__(self) -> bool:
        return bool(self.properties)
    
    def __str__(self) -> bool:
        return str(self.properties)

@dataclass
class NamedRange(GoogleWorkSpaceResourceBase):
    """https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets#namedrange"""
    namedRangeId: str = field(default="")
    name: str = field(default="")
    range: GridRange|dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.fixup()

    def fixup(self) -> None:
        self.range = self.range if isinstance(self.range,GridRange) else GridRange(**dict(self.range))

    def to_base(self) -> dict:
        self.fixup()
        b = {'namedRangeId': str(self.namedRangeId) if bool(self.namedRangeId) else None,
             'name': str(self.name) if bool(self.name) else None,
             'range': self.range if bool(self.range) else None }
        return b

@dataclass
class Spreadsheet(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets#resource:-spreadsheet
    The representation of a spreadsheet.
    """
    spreadsheetId: str = field(default="")
    properties: SpreadsheetProperties|dict = field(default_factory=dict)
    sheets: List[Sheet|dict] = field(default_factory=list)
    namedRanges: List[NamedRange|dict] = field(default_factory=list)
    spreadsheetUrl: str = field(default="")
    developerMetadata: List[dict] = field(default_factory=list)
    dataSources: List[dict] = field(default_factory=list)
    dataSourceSchedules: List[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.fixup()

    def fixup(self) -> None:
        self.properties = self.properties if isinstance(self.properties,SheetProperties) else SpreadsheetProperties(**dict(self.properties))
        self.sheets = [s if isinstance(s,Sheet) else Sheet(**dict(s)) for s in self.sheets]
        self.namedRanges = [nr if isinstance(nr,NamedRange) else NamedRange(**dict(nr)) for nr in self.namedRanges]

    def to_base(self) -> dict:
        self.fixup()
        b = asdict(self)
        b['properties'] = self.properties.to_base()
        b['sheets'] = [s.to_base() for s in self.sheets]
        b['namedRanges'] = [nr.to_base() for nr in self.namedRanges]
        return b


    def __bool__(self) -> bool:
        return bool(self.spreadsheetId)
    
    def __str__(self) -> str:
        val = 'unconnected'
        if self.spreadsheetId:
            if self.sheets:
                val = self.properties.title
                val += '['
                for s in self.sheets:
                    val += str(s)
                    val += ','
                val = val.rstrip(val[-1])
                val += ']'
            else:
                val = f"{self.spreadsheetId}(unconnected)"
        return val

