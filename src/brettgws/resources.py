from dataclasses import asdict,fields,is_dataclass
from typing import List

class GoogleWorkSpaceResourceBase():
    """
    Intended to be subclassed by a dataclass but isnt actually a dataclass.
    Provide a base __post_init__ here to just call fixup or leave it to subclasses?
    """
    def to_base(self) -> dict:
        """
        Default just return the dict representation of the object as needed by
        the GWS client.  Something more complicated can override.
        Also with a common base makes it easy to filter with isinstance.
        Call fixup() first to ensure all fields are in correct format.
        """
        self.fixup()
        return asdict(self)
    
    def trim(self) -> dict|None:
        """
        Return a 'trimmed' dict of the resource.  That is, removing any top level attributes
        that are an empty or None.  For empty needs to be a string, or container. For None
        needs to be a value like int or bool where 'not' could be a valid value.  This is
        for GWS requests that only want filled-in fields.
        Although doing some probing it turns out the GWS client already trims out fields with None
        """
        b = self.to_base()
        # now clear out any null (empty) fields as these would translate
        # to nonvalues for optional fields
        if b:
            vals = dict(b.items())
            for k,v in vals.items():
                if v is None or (type(v) not in [int,bool,float] and not v):
                    del b[k]     
        return b
    
    def fixup(self) -> None:
        """
        notify a subclass to do any field adjustments
        """
        pass
    
    def update_fields(self, **kwargs) -> List[str]:
        """
        Update fields that may be present.
        """
        updated_fields = []
        if is_dataclass(self):
            flist = fields(self)
            for k,v in kwargs.items():
                for f in flist:
                    if v is not None and k == f.name:
                        setattr(self, k, v)
                        updated_fields.append(k)
            self.fixup()
        return updated_fields
 