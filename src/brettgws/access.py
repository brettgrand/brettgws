
from collections.abc import Iterable
from pathlib import Path
import json
import copy
from functools import wraps

import google.auth
import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
import googleapiclient.discovery_cache as gws_discovery_cache

class __GWSAccess():
    """
    Class encapsulating authenticated access to Google Workspace
    See https://developers.google.com/workspace/guides/create-credentials#choose_the_access_credential_that_is_right_for_you
    for an overview of what you'll need.  Once you've obtained a secrets file you can refer the object to it
    for authentication.  For OAuth it will trigger the confirmation screens.  Sessions will be preserved
    and refreshed to confirmation does not need to happen repeatedly.
    Scopes are expected to be added by clients as needed and may trigger a refresh.

    It makes no sense to have multiple authenticated sessions per application so do this as a module singleton
    and then its simple to do the service retrieval (which is what most clients are really after) as a decorator.
    """

    __SCOPES = {
        "sheets": "https://www.googleapis.com/auth/spreadsheets",
        "sheets-ro": "https://www.googleapis.com/auth/spreadsheets.readonly",
        "drive-file": "https://www.googleapis.com/auth/drive.file",
        "drive": "https://www.googleapis.com/auth/drive",
        "drvie-ro": "https://www.googleapis.com/auth/drive.readonly",
        "calendar": "https://www.googleapis.com/auth/calendar",
        "calendar-ro": "https://www.googleapis.com/auth/calendar.readonly",
        "events": "https://www.googleapis.com/auth/calendar.events",
        "events-ro": "https://www.googleapis.com/auth/calendar.events.readonly",
        "settings-ro": "https://www.googleapis.com/auth/calendar.settings.readonly",
        "openid": "openid",
        "email": "email",
        "profile": "profile",
        "userinfo-email": "https://www.googleapis.com/auth/userinfo.email",
        "userinfo-profile": "https://www.googleapis.com/auth/userinfo.profile"
    }
    __SCOPE_URL_PREFIX = "https://www.googleapis.com/"

    __DEFAULT_AUTH_PROMPT_MSG = "MORBO DEMANDS WEAK UNAUTHENTICATED USER TO GO HERE: {url}"
    __DEFAULT_AUTH_FLOW_SUCCESS_MSG = "MORBO HAS CRUSHED PUNY OAUTH FLOW, MORBO DEMANDS THIS WINDOW CLOSED!"
    __DEFAULT_SECRETS = str((Path.home() / "gws_client_secrets.json").absolute())
    __DEFAULT_CACHE = str((Path.home() / "gws_tokens.json").absolute())

    def __init__(self) -> None:
        """
        config and scopes can be specified here but as this is a global singleton
        its more expected to add them later.
        """
        self.reset()

    def __bool__(self) -> bool:
        """True is we are connected and authenticated"""
        return self.connected
    
    def __str__(self) -> str:
        if self.connected:
            return f"Connected:{str(self.session_scopes)}"
        return f"Disconnected:{str(self.__scopes)}"
    
    def __repr__(self) -> str:
        return f"{str(self.__class__)}:{str(self)}"
    
    @classmethod
    def get_scope(cls, scope: str) -> str:
        """
        Get a scope based on simplified label.
        A raw URL will also be expected.
        """
        s = str(scope)
        sc = cls.__SCOPES.get(s, "")
        if not sc and s.startswith(cls.__SCOPE_URL_PREFIX):
            sc = s
        return sc

    @property
    def client_secrets(self) -> Path:
        """
        Path to client secrets file as provided by Google when generating access credentials.
        """
        return self.__secrets

    @client_secrets.setter
    def client_secrets(self, value: Path|str) -> None:
        """
        Set path to client secrets.
        If this changes we need to reconnect as we have new credentials.
        """
        val = value if isinstance(value, Path) else Path(str(value))
        if val != self.__secrets:
            self.__secrets = val
            if self.connected:
                self.connect()

    @property
    def cred_cache(self) -> Path:
        """
        Path to local credential cache to not have to do full authentication each time. 
        """
        return self.__cache
    
    @cred_cache.setter
    def cred_cache(self, value: Path|str):
        """
        Set path to credential cache.
        If this changes we need to reconnect as the cache is now invalid.
        """
        val = value if isinstance(value, Path) else Path(str(value))
        if val != self.__cache:
            self.__cache = val
            if self.connected:
                self.connect()

    def clear(self):
        """Reset the access state."""
        self.__creds = None
        self.__scopes = []
        self.__services = {}

    @property
    def connected(self) -> bool:
        """
        Are we authenticated with Google?
        """
        return bool(self.__creds) and bool(self.__creds.valid)
    
    @property
    def session_scopes(self) -> list[str]:
        """
        Scopes authenticated by Google for this session.
        This differs to self.scopes as that is what is requested or to be requested.
        """
        if self.connected:
            return self.__creds.scopes
        return []
    
    @property
    def scopes(self) -> list[str]:
        """
        The scopes requested or to be requested on next authentication sequence.
        """
        return self.__scopes
    
    @scopes.setter
    def scopes(self, value: None|list[str]|str) -> None:
        """
        Override a new list of session scopes.
        This will trigger a reconnect if the new list contains scopes
        that are not part of the current authenticate list.
        """
        slist = []
        if value is not None:
            slist = []
            if isinstance(value,str) or not isinstance(value,Iterable):
                s = self.get_scope(str(value))
                if s:
                    slist.append(s)
            else:
                for v in value:
                    s = self.get_scope(str(v))
                    if s:
                        slist.append(s)
        self.__scopes = slist
        if self.__scopes and self.connected:
            self.refresh()
        else:
            self.__creds = None
            self.__services = {}
    
    def append_scopes(self, *args) -> bool:
        """
        Adding to the current scope list.
        Typically it is intended that client dependent modules will add the specific
        scopes they require on init.
        """
        for a in args:
            b = [a] if isinstance(a,str) or not isinstance(a, Iterable) else a
            for i in b:
                s = self.get_scope(str(i))
                if s not in self.__scopes:
                    self.__scopes.append(s)
        return self.refresh()

    def scope_in_session(self, scope: str) -> bool:
        """
        Is the specified scope in the currently authenicated session?
        """
        s = self.get_scope(scope)
        return s and self.connected and (s in self.session_scopes)

    @property
    def creds(self) -> dict|None:
        """
        Current active access credentials or None
        """
        return self.__creds
    
    @property
    def services(self) -> dict[str,dict]:
        """
        Current active services.  Can be empty.
        """
        return self.__services

    @property
    def config(self) -> dict:
        """
        Get all configuration state as a dict.
        Convenience for getting it all at once for pushing into a json, toml, ini, etc, file.
        """
        config = {
            'secrets': self.__secrets,
            'cache': self.__cache,
            'scopes': self.__scopes,
            'server': self.auth_server,
            'port': self.auth_port
        }
        return config

    @config.setter
    def config(self, config: dict) -> None:
        """
        Set configuration state from a dict.
        Convenience method for inserting state pulled from a config file or equivalent.
        """
        reconnect = False
        v = config.get('port', None)
        if v is not None:
            self.auth_port = int(v)
        v = config.get('server', None)
        if v is not None:
            self.auth_server = str(v)
        v = config.get('scopes', [])
        if v:
            self.__scopes = v
            reconnect = True
        v = config.get('cache', None)
        if v is not None:
            self.__cache = Path(v)
            reconnect = True
        v = config.get('secrets', None)
        if v is not None:
            self.__secrets = Path(v)
            reconnect = True
        v = config.get('auth_prompt_msg', None)
        if v is not None:
            self.auth_prompt_msg = str(v)
        v = config.get('flow_success_msg', None)
        if v is not None:
            self.auth_flow_success_msg = str(v)
        if reconnect and self.connected:
            self.connect()

    @property
    def developer_key(self) -> str|None:
        return self.__developer_key
    
    @developer_key.setter
    def developer_key(self, value: str|None) -> None:
        v = value if value is None else str(value)
        if v != self.__developer_key:
            self.__services = {}
            self.__developer_key = v

    
    def reset(self) -> None:
        """
        Reset all connection state to defaults.
        """
        self.__secrets = self.__DEFAULT_SECRETS
        self.__cache = self.__DEFAULT_CACHE
        self.__discovery_cache = gws_discovery_cache.autodetect()
        self.__creds = None
        self.__scopes = []
        self.__services = {}
        self.__developer_key = None
        self.auth_server = 'localhost'
        self.auth_port = 0
        self.auth_prompt_msg = self.__DEFAULT_AUTH_PROMPT_MSG
        self.auth_flow_success_msg = self.__DEFAULT_AUTH_FLOW_SUCCESS_MSG

    def refresh(self) -> bool:
        """
        Check the current scopes and if new requested ones are not present
        in the current session_scopes, refresh the access.
        """
        scopes_accounted = all(s in self.session_scopes for s in self.__scopes)
        if self.connected and not scopes_accounted:
            return self.connect()
        return True

    def connect(self) -> bool:
        """
        Establish a new authentication session.
        If successful will save the credentials in the cache file to reuse
        on subsequent invocations.
        """
        # TODO: Set up for service accounts
        self.__creds = None
        self.__services = {}
        if not self.__scopes:
            return
        requested_scopes = copy.copy(self.__scopes)
        if (self.__cache.exists() and self.__cache.is_file()):
            # need to check what scopes are associated with this cache
            # I'm not sure why GWS doesn't resolve that when you refresh,
            # but there we are
            cf = self.__cache.resolve()
            with open(cf, 'r', encoding='utf-8') as f:
                j = json.load(f)
                scopes = j.get('scopes',[])
                if not all(s in scopes for s in requested_scopes):
                    self.__cache.unlink()
                else:
                    self.__creds = Credentials.from_authorized_user_file(cf, requested_scopes)
        if not self.connected:
            if self.__creds and self.__creds.refresh_token:
                try:
                    self.__creds.refresh(Request())
                except Exception as e:
                    print(f'failed to refresh stored creds: {str(e)}...deleting cred cache and re-authorizing')
                finally:
                    if not self.connected:
                        self.__cache.unlink()

            if not self.connected:
                if self.__secrets.exists() and self.__secrets.is_file():
                    flow = InstalledAppFlow.from_client_secrets_file(self.__secrets, requested_scopes)
                    self.__creds = flow.run_local_server(self.auth_server, self.auth_port,
                                                    authorization_prompt_message=self.auth_prompt_msg,
                                                    success_message=self.auth_flow_success_msg
                                                    )
                else:
                    # final hail mary
                    try:
                        # this will look at the GOOGLE_APPLICATION_CREDENTIALS envvar and
                        # other cloud default locations
                        self.__creds, _ = google.auth.default(requested_scopes)
                    except google.auth.exceptions.DefaultCredentialsError:
                        pass

            if self.connected:
                # whoa it took a while to track through what was needed for a refresh
                # scopes isnt even necessary, that's just to see what the scopes were
                # we could feed them back in to from_authorized_user_file but the caller may have different scopes in mind
                user_info = {'refresh_token': self.__creds.refresh_token, 'client_id': self.__creds.client_id, 
                            'client_secret': self.__creds.client_secret, 'scopes': requested_scopes}
                with open(self.__cache.resolve(), 'w', encoding='utf-8') as f:
                    json.dump(user_info, f, ensure_ascii=False, indent=2)
        return self.connected
    
    def get_service(self, name: str, version: str) -> Resource|None:
        """
        Build the requested service if not already available, connecting if required.
        Can return None if no connection present. 
        """
        if not self.connected:
            self.connect()
        if not self.connected:
            return None
        id = f'{name}:{version}'
        s = self.__services.get(id, None)
        if s is None:
            s = build(name, version, credentials=self.__creds,
                      developerKey=self.__developer_key, cache=self.__discovery_cache)
            if s:
                self.__services[id] = s
        return s

gws = __GWSAccess()

def service(name: str, version: str):
    """
    Simple decorator to deliver the required service to a function that
    needs access to a GWS service to build a request.
    param: name: service name
    param: version: service version
    """
    def _inner_decorator(f):
        @wraps(f)
        def wrapped(*args,**kwargs):
            s = gws.get_service(name, version)
            kwargs['service'] = s
            response = f(*args, **kwargs)
            return response
        return wrapped
    return _inner_decorator

            
