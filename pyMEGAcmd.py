from .lib.helper import MEGAcmdWrapperABC, CMDResult
import subprocess
from typing import Optional, Literal
import re
from dataclasses import dataclass
import logging

LOGGER = logging.getLogger(__name__) # Logger

@dataclass
class MEGADirectoryEntry: 
    """Used for MEGAcmdWrapper.cmd_ls results."""
    name: str # Name of the file or directory
    date: str
    handle: str # Handle identifier
    is_directory: bool # True if directory, False if file
    flags: str # Entry flags (e.g., '-ep-')
    size: Optional[str] = None # Size (for files)

@dataclass
class MEGAExportEntry:
    """Used for 
        MEGAcmdWrapper.cmd_export
        MEGAcmdWrapper.cmd_export__add
        MEGAcmdWrapper.cmd_export__list
    results."""
    remote_path: str
    link: str
    size: Optional[str] = None # None for folders
    is_folder: bool = False
    auth_token: Optional[str] = None # If present

class MEGAcmdWrapper(MEGAcmdWrapperABC):
    """Wrapper for MEGAclient command line tool (MEGAcmd)."""
    RE_WHOAMI_EMAIL = re.compile(r'Account e-mail: (.+?)$')
    RE_LOGOUT_SESSION = re.compile(r'session id: (.+?)$')
    RE_EXPORT__LIST_FILE = re.compile(r'^(.+) \(([^,]+), shared as exported permanent file link: ([^\)]+)\)$')
    RE_EXPORT__LIST_FOLDER = re.compile(r'^(.+) \(folder, shared as exported permanent folder link: ([^\)]+)\)$')
    RE_EXPORT__LIST_AUTHTOKEN = re.compile(r'^(.+) AuthToken=(.+?)$')
    RE_EXPORT__ADD_FOLDER = re.compile(r'^Exported (.+?): (ht.+?)\n\s+AuthToken = (.+)$')
    RE_EXPORT__ADD_FILE = re.compile(r'^Exported (.+?): (ht.+?)$')

    def __init__(self, mega_cmd_path: str, check_path: bool = True) -> None:
        """Wrapper for MEGAclient command line tool (MEGAcmd).
        
        Args:
            mega_cmd_path (str): Path to MEGAclient executable.
            check_path (bool): Whether to check if the executable path exists upon initialization. Defaults to True.
        """
        super().__init__()
        self.mega_cmd_path = mega_cmd_path

        if check_path: # Check if path exists
            try: 
                self.cmd_version()
            except FileNotFoundError as e:
                raise FileNotFoundError(f"MEGAclient executable not found at path: {mega_cmd_path}") from e

    def _run_mega_cmd(self, args: list[str]) -> CMDResult:
        """
        Run the MEGAclient command with the provided arguments.

        Args:
            args (list[str]): List of arguments to pass to MEGAclient.

        Returns:
            str: Output from the MEGAclient command.
        """
        command = [self.mega_cmd_path] + args
        LOGGER.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        cmd_res = CMDResult(stdout=result.stdout.strip(), stderr=result.stderr.strip(), return_code=result.returncode)
        LOGGER.debug(f'Command returned {cmd_res=}')
        return cmd_res

    def cmd_export(
            self, 
            action: Literal['add', 'delete', 'list'], 
            remote_path: Optional[str] = None, 
            writeable: bool = False, 
            password: Optional[str] = None
        ) -> None | MEGAExportEntry | bool | list[MEGAExportEntry]:
        """Export (link creation) command wrapper.
        
        Note: It is recommended to use the specific subcommand methods instead:
            - cmd_export__add
            - cmd_export__delete
            - cmd_export__list
        as they provide better type hints and clarity.
        
        Args:
            action (Literal['add', 'delete', 'list']): Action to perform.
            remote_path (Optional[str]): Remote path for the action.
            writeable (bool): Whether the export link should be writeable (folders only). Defaults to False. "add" action only.
            password (Optional[str]): Password to protect the link with, available for pro users only. Defaults to None. "add" action only.
        """
        if action == 'add':
            assert remote_path is not None, "remote_path is required for adding an export."
            return self.cmd_export__add(remote_path, writeable, password)
        elif action == 'delete':
            assert remote_path is not None, "remote_path is required for deleting an export."
            assert not writeable, "writeable parameter is not applicable for delete action."
            assert password is None, "password parameter is not applicable for delete action."
            return self.cmd_export__delete(remote_path)
        elif action == 'list':
            assert not writeable, "writeable parameter is not applicable for delete action."
            assert password is None, "password parameter is not applicable for delete action."
            return self.cmd_export__list(remote_path)
        else:
            raise ValueError(f"Invalid action: {action}. Must be 'add', 'delete', or 'list'.")
    
    def cmd_export__add(
            self, 
            remote_path: str, 
            writeable: bool = False, 
            password: Optional[str] = None
        ) -> MEGAExportEntry | None:
        """Export (link creation), add subcommand.

        Will add an export (create link) to given remote_path.

        Args:
            remote_path (str): Remote path to add export to
            writeable (bool): Whether the export link should be writeable (folders only). Defaults to False.
            password (Optional[str]): Password to protect the link with, available for pro users only. Defaults to None.
        
        Returns:
            MEGAExportEntry | None: Export entry if successful, None otherwise.
        Note: MEGAExportEntry.size will always be None (not known).
        """
        command = ["export", "-f", "-a", remote_path]
        command += [] if not writeable else ["--writable"]
        command += [] if password is None else [f"--password={password}"]
        res = self._run_mega_cmd(command)
        
        if res.return_code != 0:
            LOGGER.error("Failed to add export:\n" + res.stderr)
            return None
        
        if "Only PRO users can protect links with passwords" in res.stderr:
            LOGGER.warning("Password protection is a PRO feature. Export created without password.")
        
        match1 = self.RE_EXPORT__ADD_FOLDER.search(res.stdout)
        match2 = self.RE_EXPORT__ADD_FILE.search(res.stdout)
        if match1:
            path, link, auth_token = match1.groups()
            return MEGAExportEntry(path, link, is_folder=True, auth_token=auth_token)
        elif match2:
            path, link = match2.groups()
            return MEGAExportEntry(path, link, is_folder=False, auth_token=None)
        else:
            LOGGER.error("Unexpected export add output:\n" + res.stdout)
        return None
        
    def cmd_export__delete(self, remote_path: str) -> bool:
        """Export (link creation), delete subcommand.

        Will delete the export at given remote_path.

        Args:
            remote_path (str): Remote path to delete export from.
        
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        command = ["export", "-d", remote_path]
        res = self._run_mega_cmd(command)
        if res.return_code != 0:
            LOGGER.error("Failed to delete export:\n" + res.stderr)
            return False
        return True
    
    def cmd_export__list(self, remote_path: Optional[str] = None) -> list[MEGAExportEntry]:
        """Export (link creation), list subcommand.

        Will list all exports under remote_path tree if provided, or under current remote directory if not.

        Args:
            remote_path (Optional[str]): Remote path to list exports from.
        
        Returns:
            list[MEGAExportEntry]: List of export entries.
        """
        command = ["export"] + ([] if remote_path is None else [remote_path])
        res = self._run_mega_cmd(command)
        if res.return_code != 0:
            LOGGER.error("Failed to list exports:\n" + res.stderr)
            return []
        
        entries: list[MEGAExportEntry] = []
        for line in res.stdout.strip().splitlines():
            match_file = self.RE_EXPORT__LIST_FILE.match(line)
            match_folder = self.RE_EXPORT__LIST_FOLDER.match(line)
            if match_file:
                path, size, link = match_file.groups()
            elif match_folder:
                path, link = match_folder.groups()
            else:
                raise RuntimeError("Unexpected export list line format:\n" + line)
            match_auth = self.RE_EXPORT__LIST_AUTHTOKEN.match(link)
            if match_auth:
                link, auth_token = match_auth.groups()
            else:
                auth_token = None
            
            entry = MEGAExportEntry(
                remote_path=path,
                link=link,
                size=size if match_file else None,
                is_folder=bool(match_folder),
                auth_token=auth_token
            )
            entries.append(entry)

        return entries
    
    def cmd_login(
            self, 
            email: Optional[str] = None, 
            password: Optional[str] = None, 
            auth_code: Optional[str] = None,
            session: Optional[str] = None
        ) -> bool:
        """Log in to MEGA account.
        
        Args:
            USER LOGIN:
                email (str): User email.
                password (str): User password.
                auth_code (Optional[str]): Two-factor authentication code if applicable.
            SESSION LOGIN:
                session (str): Session string if applicable.
            EXPORTED FOLDER URL LOGIN:
                # TODO
            PASSWORD PROTECTED LINK LOGIN:
                # TODO
            
        Returns:
            bool: True if login was successful, False otherwise.

        Note: Use either one of the above login methods at a time.
        """
        is_user_login = any([email, password, auth_code])
        is_session_login = session is not None
        if sum([is_user_login, is_session_login]) != 1:
            raise ValueError("Invalid login parameters. Use only one login method.")

        if is_user_login:
            assert email is not None and password is not None, "Email and password are required for user login."
            command = ['login', email, password]
            if auth_code:
                command.append(f"--auth-code={auth_code}")
            res = self._run_mega_cmd(command)
            
            if res.return_code != 0:
                return False
            return True
        elif is_session_login:
            assert session is not None, "Session string is required for session login."
            command = ['login', session]
            res = self._run_mega_cmd(command)
            
            if res.return_code != 0:
                return False
            return True
        return False  # Fallback, should not reach here.

    def cmd_logout(self, keep_session: bool = False) -> tuple[bool, None | str]:
        """Log out from MEGA account.
        
        Returns tuple[success, session]:
            success (bool): True if logout was successful, False otherwise.
            session (None | str): Session string if applicable, None otherwise.
            """
        command = ['logout']
        if keep_session:
            command.append('--keep-session')
        res = self._run_mega_cmd(command)
        
        if res.return_code != 0:
            return (False, None)
        session = None
        if keep_session:
            match = self.RE_LOGOUT_SESSION.search(res.stdout)
            if match:
                session = match.group(1)
        return (True, session)
    
    def cmd_ls(self, remote_path: str = '/') -> list[MEGADirectoryEntry]:
        """"""
        command = ["ls", "-hal", "--show-handles", remote_path]

        res = self._run_mega_cmd(command)
        if res.return_code != 0:
            raise RuntimeError("Failed to list directory:\n" + res.stderr)
        
        dir_entries: list[MEGADirectoryEntry] = []
        for line in res.stdout.strip().splitlines()[1:]:
            # Assumes format and spacing is consistent
            flags = line[0:4].strip()
            version = line[4:9].strip()
            if version == '-':
                version = None
            size = line[9:22].strip()
            if size == '-':
                size = None
            date = line[22:41].strip()
            handle = line[41:52].strip()
            name = line[52:].strip()
            is_directory = flags[0] == 'd'
            entry = MEGADirectoryEntry(
                name=name,
                date=date,
                handle=handle,
                is_directory=is_directory,
                flags=flags,
                size=size
            )
            dir_entries.append(entry)       
        return dir_entries
    
    def cmd_tree(self, remote_path: Optional[str] = None) -> str:
        """Get the remote directory tree structure.

        Args:
            remote_path (Optional[str]): Remote path to get tree from. If None, tree under current remote directory. Defaults to None.
        Returns:
            str: Directory tree structure as a string.
        """
        command = ["tree"] + ([] if remote_path is None else [remote_path])
        res = self._run_mega_cmd(command)
        if res.return_code != 0:
            raise RuntimeError("Failed to get directory tree:\n" + res.stderr)
        return res.stdout.strip()
    
    def cmd_version(self) -> str:
        """
        Get the MEGAclient version.

        Returns:
            str: MEGAclient version string.
        """
        res = self._run_mega_cmd(['version'])
        return res.stdout.strip()

    def cmd_whoami(self) -> str | None:
        """
        Get the current logged in user.

        Returns:
            str | None: Logged in user email or None if not logged in.
        """
        res = self._run_mega_cmd(['whoami'])

        # Not logged in or error
        if res.return_code != 0:
            return None
        
        # Email (logged-in user)
        match = self.RE_WHOAMI_EMAIL.search(res.stdout)
        if match:
            return match.group(1)
        
        # Misc
        raise NotImplementedError("Unexpected output from whoami command:\n" + res.stdout)
    