from .helper import MEGAcmdWrapperABC, CMDResult, clean_remote_path, clean_local_path
import subprocess
from typing import Optional, Literal, Iterable
import re
from dataclasses import dataclass
import logging

LOGGER = logging.getLogger(__name__)  # Logger


@dataclass
class MEGADirectoryEntry:
    """Used for 
        MEGAcmdWrapper.cmd_ls
        MEGAcmdWrapper.cmd_find     
    results."""

    name: str  # Name of the file or directory
    handle: str  # Handle identifier
    is_directory: bool  # True if directory, False if file
    flags: Optional[str] = None  # Entry flags (e.g., '-ep-')
    date: Optional[str] = None  # Date string
    size: Optional[str] = None  # Size (for files)
    link: Optional[str] = None  # Exported link if applicable


@dataclass
class MEGADiskFreeResult:
    """Used for MEGAcmdWrapper.cmd_df results."""

    cloud_drive_used: int  # Bytes used in cloud drive
    cloud_drive_files: int  # Number of files in cloud drive
    cloud_drive_folders: int  # Number of folders in cloud drive
    inbox_used: int  # Bytes used in inbox
    inbox_files: int  # Number of files in inbox
    inbox_folders: int  # Number of folders in inbox
    rubbish_bin_used: int  # Bytes used in rubbish bin
    rubbish_bin_files: int  # Number of files in rubbish bin
    rubbish_bin_folders: int  # Number of folders in rubbish bin
    total_used_storage: int  # Bytes used in total
    used_storage_percentage: float  # Percentage of used storage [0.0 - 100.0]
    total_storage: int  # Bytes of total storage the user has
    size_file_versions: int  # Bytes used by file versions


@dataclass
class MEGAExportEntry:
    """Used for
        MEGAcmdWrapper.cmd_export
        MEGAcmdWrapper.cmd_export__add
        MEGAcmdWrapper.cmd_export__list
    results."""

    remote_path: str
    link: str
    size: Optional[str] = None  # None for folders
    is_folder: bool = False
    auth_token: Optional[str] = None  # If present

@dataclass
class MEGADuEntry:
    """Used for MEGAcmdWrapper.cmd_du results."""

    remote_path: str
    size: int  # Bytes, size of the file or folder
    size_with_versions: int  # Bytes, size including file versions

@dataclass
class MEGADuResult:
    """Used for MEGAcmdWrapper.cmd_du results."""

    entries: list[MEGADuEntry]
    size_total: int  # Bytes, total size of all entries
    size_total_with_versions: int  # Bytes, total size including file versions

class MEGAcmdWrapper(MEGAcmdWrapperABC):
    """Wrapper for MEGAclient command line tool (MEGAcmd)."""

    RE_DF_CLOUD = re.compile(
        r"Cloud drive:\s+(\d+) in\s+(\d+) file\(s\) and\s+(\d+) folder\(s\)"
    )
    RE_DF_INBOX = re.compile(
        r"Inbox:\s+(\d+) in\s+(\d+) file\(s\) and\s+(\d+) folder\(s\)"
    )
    RE_DF_BIN = re.compile(
        r"Rubbish bin:\s+(\d+) in\s+(\d+) file\(s\) and\s+(\d+) folder\(s\)"
    )
    RE_DF_TOTAL = re.compile(r"USED STORAGE:\s+(\d+)\s+([\d\.]+)% of\s+(\d+)")
    RE_DF_VERSIONS = re.compile(r"Total size taken up by file versions:\s+(\d+)")
    RE_DU_TOTAL = re.compile(r"^Total storage used:\s+(\d+)\s+(\d+)$")
    RE_DU_ENTRY = re.compile(r"^([^:]+):\s+(\d+)\s+(\d+)$")
    RE_EXPORT__LIST_FILE = re.compile(
        r"^(.+) \(([^,]+), shared as exported permanent file link: ([^\)]+)\)$"
    )
    RE_EXPORT__LIST_FOLDER = re.compile(
        r"^(.+) \(folder, shared as exported permanent folder link: ([^\)]+)\)$"
    )
    RE_EXPORT__LIST_AUTHTOKEN = re.compile(r"^(.+) AuthToken=(.+?)$")
    RE_EXPORT__ADD_FOLDER = re.compile(
        r"^Exported (.+?): (ht.+?)\n\s+AuthToken = (.+)$"
    )
    RE_EXPORT__ADD_FILE = re.compile(r"^Exported (.+?): (ht.+?)$")
    RE_FIND_FILE_EXPORTED = re.compile(r"^([^<]+) <([\w\d:]+)> \(([^,\)]+),[^:]+: (.+)\)$")
    RE_FIND_FILE = re.compile(r"^([^<]+) <([\w\d:]+)> \(([^\)]+)\)$")
    RE_FIND_FOLDER_EXPORTED = re.compile(r"^([^<]+) <([\w\d:]+)> \(folder, [^:]+: (.+)\)$")
    RE_FIND_FOLDER = re.compile(r"^([^<]+) <([\w\d:]+)> \(folder\)$")
    RE_LOGOUT_SESSION = re.compile(r"session id: (.+?)$")
    RE_SESSION = re.compile(r"^Your \(secret\) session is:\s+(.+)$")
    RE_WHOAMI_EMAIL = re.compile(r"Account e-mail: (.+?)$")

    def __init__(self, mega_cmd_path: str, check_path: bool = True) -> None:
        """Wrapper for MEGAclient command line tool (MEGAcmd).

        Args:
            mega_cmd_path (str): Path to MEGAclient executable.
            check_path (bool): Whether to check if the executable path exists upon initialization. Defaults to True.
        """
        super().__init__()
        self.mega_cmd_path = mega_cmd_path

        if check_path:  # Check if path exists
            try:
                self.cmd_version()
            except FileNotFoundError as e:
                raise FileNotFoundError(
                    f"MEGAclient executable not found at path: {mega_cmd_path}"
                ) from e

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
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8"
        )
        cmd_res = CMDResult(
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            return_code=result.returncode,
        )
        LOGGER.debug(f"Command returned {cmd_res=}")
        return cmd_res

    def cmd_cat(self, remote_paths: Iterable[str]) -> str:
        """Get remote file contents.

        Args:
            remote_paths (Iterable[str]): Iterable of remote file paths to get contents from.

        Returns:
            str: Concatenated contents of the remote files.

        Note:
            The returned string will have the contents of all files concatenated together using '\n\n' as separator, provided by MEGAcmd.
            Appropriate file parsing should be implemented by the user if needed when multiple files are provided.
        """
        assert not isinstance(
            remote_paths, str
        ), "remote_paths must be an iterable of strings, not a string."
        command = ["cat"]
        command += [clean_remote_path(path) for path in remote_paths]
        res = self._run_mega_cmd(command)

        print(res)
        if res.return_code == 0:
            return res.stdout.strip()

        elif res.return_code == 53:  # Not found
            LOGGER.error(f"Remote path not found: {res}")
            raise RuntimeError(f"Remote path not found: {res}")

        elif res.return_code == 51:  # Not a file
            LOGGER.error(f"Remote path is not a file: {res}")
            raise RuntimeError(f"Remote path is not a file: {res}")

        raise RuntimeError(f"Unknown error in cat command: {res}")

    def cmd_cd(self, remote_path: str) -> bool:
        """Change current remote directory.

        Args:
            remote_path (str): Remote path to change to. Can be absolute or relative.

        Note:
            MEGAcmd supports ommiting remote_path but this changes nothing so I made it required here.

        """

        command = ["cd"]
        command += [] if remote_path is None else [clean_remote_path(remote_path)]
        res = self._run_mega_cmd(command)

        if res.return_code == 0:
            return True
        elif res.return_code == 53:  # Not found
            LOGGER.error(f"Remote path not found: {res}")
            return False

        raise RuntimeError(f"Failed to change directory: {res.stderr}")

    def cmd_df(self) -> MEGADiskFreeResult:
        """Get remote storage usage information.

        Returns:
            MEGADiskFreeResult: Storage usage information.

        Raises:
            RuntimeError: If the command fails.
        """
        res = self._run_mega_cmd(["df"])

        # Init to 0
        cloud_drive_used = cloud_drive_files = cloud_drive_folders = 0
        inbox_used = inbox_files = inbox_folders = 0
        rubbish_bin_used = rubbish_bin_files = rubbish_bin_folders = 0
        total_used_storage = total_storage = size_file_versions = 0
        used_storage_percentage = 0.0

        if res.return_code == 0:
            for line in res.stdout.strip().splitlines():
                match_cloud = self.RE_DF_CLOUD.match(line)
                match_inbox = self.RE_DF_INBOX.match(line)
                match_bin = self.RE_DF_BIN.match(line)
                match_total = self.RE_DF_TOTAL.match(line)
                match_versions = self.RE_DF_VERSIONS.match(line)

                if match_cloud:
                    cloud_drive_used = int(match_cloud.group(1))
                    cloud_drive_files = int(match_cloud.group(2))
                    cloud_drive_folders = int(match_cloud.group(3))
                if match_inbox:
                    inbox_used = int(match_inbox.group(1))
                    inbox_files = int(match_inbox.group(2))
                    inbox_folders = int(match_inbox.group(3))
                if match_bin:
                    rubbish_bin_used = int(match_bin.group(1))
                    rubbish_bin_files = int(match_bin.group(2))
                    rubbish_bin_folders = int(match_bin.group(3))
                if match_total:
                    total_used_storage = int(match_total.group(1))
                    used_storage_percentage = float(match_total.group(2))
                    total_storage = int(match_total.group(3))
                if match_versions:
                    size_file_versions = int(match_versions.group(1))

            return MEGADiskFreeResult(
                cloud_drive_used=cloud_drive_used,
                cloud_drive_files=cloud_drive_files,
                cloud_drive_folders=cloud_drive_folders,
                inbox_used=inbox_used,
                inbox_files=inbox_files,
                inbox_folders=inbox_folders,
                rubbish_bin_used=rubbish_bin_used,
                rubbish_bin_files=rubbish_bin_files,
                rubbish_bin_folders=rubbish_bin_folders,
                total_used_storage=total_used_storage,
                used_storage_percentage=used_storage_percentage,
                total_storage=total_storage,
                size_file_versions=size_file_versions,
            )

        raise RuntimeError("Failed to get storage usage:\n" + res.stderr)

    def cmd_du(self, remote_paths: Iterable[str]) -> MEGADuResult:
        """Get disk usage of remote files/folders.
        
        Args:
            remote_paths (Iterable[str]): Iterable of remote file or folder paths to get disk usage for.
        Returns:
            MEGADuResult: Disk usage information for the provided remote paths.
        Raises:
            RuntimeError: If the command fails.
        """
        assert not isinstance(
            remote_paths, str
        ), "remote_paths must be an iterable of strings, not a string."
        command = ["du", "--versions"]
        command += [clean_remote_path(path) for path in remote_paths]
        res = self._run_mega_cmd(command)
        if res.return_code != 0:
            raise RuntimeError(f"Failed to get disk usage: {res.stderr}")
        entries: list[MEGADuEntry] = []
        total_size = total_size_with_versions = 0
        for line in res.stdout.strip().splitlines():
            sline = line.strip()
            match_total = self.RE_DU_TOTAL.match(sline)
            match_entry = self.RE_DU_ENTRY.match(sline)
            if match_total:
                total_size = int(match_total.group(1))
                total_size_with_versions = int(match_total.group(2))
            elif match_entry:
                path, size, size_with_versions = match_entry.groups()
                entry = MEGADuEntry(
                    remote_path=path,
                    size=int(size),
                    size_with_versions=int(size_with_versions),
                )
                entries.append(entry)
        return MEGADuResult(
            entries=entries,
            size_total=total_size,
            size_total_with_versions=total_size_with_versions,
        )

    def cmd_export(
        self,
        action: Literal["add", "delete", "list"],
        remote_path: Optional[str] = None,
        writeable: bool = False,
        password: Optional[str] = None,
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
        if action == "add":
            assert (
                remote_path is not None
            ), "remote_path is required for adding an export."
            return self.cmd_export__add(remote_path, writeable, password)
        elif action == "delete":
            assert (
                remote_path is not None
            ), "remote_path is required for deleting an export."
            assert (
                not writeable
            ), "writeable parameter is not applicable for delete action."
            assert (
                password is None
            ), "password parameter is not applicable for delete action."
            return self.cmd_export__delete(remote_path)
        elif action == "list":
            assert (
                not writeable
            ), "writeable parameter is not applicable for delete action."
            assert (
                password is None
            ), "password parameter is not applicable for delete action."
            return self.cmd_export__list(remote_path)
        else:
            raise ValueError(
                f"Invalid action: {action}. Must be 'add', 'delete', or 'list'."
            )

    def cmd_export__add(
        self, remote_path: str, writeable: bool = False, password: Optional[str] = None
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
        command = ["export", "-f", "-a", clean_remote_path(remote_path)]
        command += [] if not writeable else ["--writable"]
        command += [] if password is None else [f"--password={password}"]
        res = self._run_mega_cmd(command)

        if res.return_code != 0:
            LOGGER.error("Failed to add export:\n" + res.stderr)
            return None

        if "Only PRO users can protect links with passwords" in res.stderr:
            LOGGER.warning(
                "Password protection is a PRO feature. Export created without password."
            )

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
        command = ["export", "-d", clean_remote_path(remote_path)]
        res = self._run_mega_cmd(command)
        if res.return_code != 0:
            LOGGER.error("Failed to delete export:\n" + res.stderr)
            return False
        return True

    def cmd_export__list(
        self, remote_path: Optional[str] = None
    ) -> list[MEGAExportEntry]:
        """Export (link creation), list subcommand.

        Will list all exports under remote_path tree if provided, or under current remote directory if not.

        Args:
            remote_path (Optional[str]): Remote path to list exports from.

        Returns:
            list[MEGAExportEntry]: List of export entries.
        """
        command = ["export"] + (
            [] if remote_path is None else [clean_remote_path(remote_path)]
        )
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
                auth_token=auth_token,
            )
            entries.append(entry)

        return entries

    def cmd_find(
            self, 
            remote_path: Optional[str] = None, 
            pattern: Optional[str] = None,
            time_constraint: Optional[str] = None,
            size_constraint: Optional[str] = None,
        ) -> list[MEGADirectoryEntry]:
        """Find files and folders in remote directory tree.

        Args:
            remote_path (Optional[str]): Remote path to start search from. If None, will be current remote directory.
            pattern (Optional[str]): Pattern to match file/folder names against. If None, will match all names.
            time_constraint (Optional[str]): Time constraint for filtering files/folders.
            size_constraint (Optional[str]): Size constraint for filtering files/folders.
        Returns:
            list[MEGADirectoryEntry]: List of found directory entries.
        
        Note:
            Date and flags will always be None (not provided by MEGAcmd).
            Size only applicable for files.
            Link will be provided for exported files/folders.
        """
        command = ["find", "-l", "--show-handles"] 
        command += [] if time_constraint is None else [f"--mtime={time_constraint}"]
        command += [] if size_constraint is None else [f"--size={size_constraint}"]
        command += [] if remote_path is None else [clean_remote_path(remote_path)]
        command += [] if pattern is None else [f"--pattern={pattern}"]
        res = self._run_mega_cmd(command)

        if res.return_code != 0:
            raise RuntimeError("Failed to find files/folders:\n" + res.stderr)

        entries: list[MEGADirectoryEntry] = []
        for line in res.stdout.strip().splitlines():
            sline = line.strip()
            if sline:
                match_folder_e = self.RE_FIND_FOLDER_EXPORTED.match(sline)
                match_folder = self.RE_FIND_FOLDER.match(sline)
                match_file_e = self.RE_FIND_FILE_EXPORTED.match(sline)
                match_file = self.RE_FIND_FILE.match(sline)
                if match_folder_e:
                    name, handle, link = match_folder_e.groups()
                    entry = MEGADirectoryEntry(
                        name=name,
                        handle=handle,
                        is_directory=True,
                        link=link
                    )
                    entries.append(entry)
                elif match_folder:
                    name, handle = match_folder.groups()
                    entry = MEGADirectoryEntry(
                        name=name,
                        handle=handle,
                        is_directory=True,
                        link=None
                    )
                    entries.append(entry)
                elif match_file_e:
                    name, handle, size, link = match_file_e.groups()
                    entry = MEGADirectoryEntry(
                        name=name,
                        handle=handle,
                        is_directory=False,
                        size=size,
                        link=link
                    )
                    entries.append(entry)
                elif match_file:
                    name, handle, size = match_file.groups()
                    entry = MEGADirectoryEntry(
                        name=name,
                        handle=handle,
                        is_directory=False,
                        size=size,
                        link=None
                    )
                    entries.append(entry)
                else:
                    raise RuntimeError("Unexpected find line format:\n" + line)
        return entries

    def cmd_get(
        self,
        path_remote: str,
        path_local: Optional[str] = None,
        password: Optional[str] = None,
        merge: bool = False,
    ) -> bool:
        """Download a file or folder.

        Args:
            path_remote (str): Remote path to file or folder to download.
            path_local (Optional[str]): Local path to download to. If None, will be current local directory.
            password (Optional[str]): Password for password-protected links. Defaults to None.
            merge (bool): Whether to merge with existing local folder when downloading a folder. Defaults to False.
        Return:
            bool: True if download was successful, False otherwise.

        Raises:
            RuntimeError: If download fails, error details will be included in the exception message.

        Note:
            - if merge is True:
                - If downloading a file, local_path will be assumed to be a file path.
                - If downloading a folder, local_path will be assumed to be a directory path and the remote directory contents will be copied into it.
            - if merge is False:
                - If downloading a file or a folder, the remote item will be downloaded into local_path.
        """
        command = ["get"]
        command += [] if not merge else ["-m"]
        command += [] if password is None else [f"--password={password}"]
        command += [
            clean_remote_path(path_remote)
        ]  # Remove trailing slash for consistency
        command += [] if path_local is None else [clean_local_path(path_local)]
        res = self._run_mega_cmd(command)

        if res.return_code == 0:
            if "Download finished" in res.stdout:
                return True

        elif res.return_code == 53:  # Not found
            LOGGER.error(f"Remote path not found: {res}")
            raise RuntimeError(f"Remote path not found: {res}")

        elif res.return_code == 54:  # Local path error
            LOGGER.error(f"Local path error: {res}")
            raise RuntimeError(f"Local path error: {res}")

        elif res.return_code == 55:  # Invalid download folder
            LOGGER.error(
                f"Invalid download folder (local folder does not exist): {res}"
            )
            raise RuntimeError(
                f"Invalid download folder (local folder does not exist): {res}"
            )

        elif res.return_code != 0:
            LOGGER.error(f"Failed to get file/folder: {res}")
            raise RuntimeError(f"Failed to get file/folder: {res}")

        return False

    def cmd_import(
        self,
        exported_link: str,
        remote_path: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """"""
        command = ["import"]
        command += [exported_link]
        command += [] if password is None else [f"--password={password}"]
        command += [] if remote_path is None else [clean_remote_path(remote_path)]
        res = self._run_mega_cmd(command)

        if res.return_code == 0:
            if "Imported folder complete:" in res.stdout:
                return True
            elif "Imported file complete:" in res.stdout:
                return True

        elif res.return_code == 55:  # Invalid remote path
            LOGGER.error(f"Invalid remote path (Invalid destiny): {res}")
            raise RuntimeError(f"Invalid remote path (Invalid destiny): {res}")

        raise RuntimeError(f"Failed to import link: {res}")

    def cmd_login(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        auth_code: Optional[str] = None,
        session: Optional[str] = None,
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
            assert (
                email is not None and password is not None
            ), "Email and password are required for user login."
            command = ["login", email, password]
            if auth_code:
                command.append(f"--auth-code={auth_code}")
            res = self._run_mega_cmd(command)

            if res.return_code != 0:
                return False
            return True
        elif is_session_login:
            assert session is not None, "Session string is required for session login."
            command = ["login", session]
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
        command = ["logout"]
        if keep_session:
            command.append("--keep-session")
        res = self._run_mega_cmd(command)

        if res.return_code != 0:
            return (False, None)
        session = None
        if keep_session:
            match = self.RE_LOGOUT_SESSION.search(res.stdout)
            if match:
                session = match.group(1)
        return (True, session)

    def cmd_lcd(self, local_path: str) -> bool:
        """Change current local directory.
        
        Args:
            local_path (str): Local path to change to.
        Returns:
            bool: True if directory change was successful, False otherwise.
            
        Note: 
            If a relative path is provided, it will be relative to the shell (python) current working directory, not the MEGAcmd local directory."""
        command = ["lcd", clean_local_path(local_path)]
        res = self._run_mega_cmd(command)
        
        if res.return_code == 0:
            return True
        elif res.return_code == 55:  # Local path error
            LOGGER.error(f"Local path error: {res}")
            return False
        raise RuntimeError(f"Failed to change local directory: {res}")
        
    def cmd_lpwd(self) -> str:
        """Get current local directory.
        
        Returns:
            str: Current local directory path.
        """
        command = ["lpwd"]
        res = self._run_mega_cmd(command)
        return res.stdout.strip()
    
    def cmd_ls(self, remote_path: str = "/") -> list[MEGADirectoryEntry]:
        """List remote directory contents.
        
        Args:
            remote_path (str): Remote path to list. Defaults to root ("/").
        Returns:
            list[MEGADirectoryEntry]: List of directory entries.
        Raises:
            RuntimeError: If the command fails.
        
        Note: Link will not be included in the results.
        """
        command = ["ls", "-hal", "--show-handles", clean_remote_path(remote_path)]

        res = self._run_mega_cmd(command)
        if res.return_code != 0:
            raise RuntimeError("Failed to list directory:\n" + res.stderr)

        dir_entries: list[MEGADirectoryEntry] = []
        for line in res.stdout.strip().splitlines()[1:]:
            # Assumes format and spacing is consistent
            flags = line[0:4].strip()
            version = line[4:9].strip()
            if version == "-":
                version = None
            size = line[9:22].strip()
            if size == "-":
                size = None
            date = line[22:41].strip()
            handle = line[41:52].strip()
            name = line[52:].strip()
            is_directory = flags[0] == "d"
            entry = MEGADirectoryEntry(
                name=name,
                date=date,
                handle=handle,
                is_directory=is_directory,
                flags=flags,
                size=size,
            )
            dir_entries.append(entry)
        return dir_entries

    def cmd_put(
        self, local_path: str | Iterable[str], remote_path: Optional[str] = None
    ) -> bool:
        """Upload one or more local files/folders to remote path.

        Args:
            local_path (str | Iterable[str]): Local file or folder path to upload, or an iterator for multiple paths.
            remote_path (Optional[str]): Remote path to upload to. If None, will upload to current remote directory.
        Note:
            - Remote path must be set when uploading multiple local items.
            - If multiple local items are provided, remote_path will be assumed to be a directory.
        """
        if isinstance(local_path, str):
            local_paths = [clean_local_path(local_path)]
        else:  # Iterator[str]
            assert (
                remote_path is not None
            ), "remote_path must be set when uploading multiple local items."
            local_paths = [clean_local_path(path) for path in local_path]

        command = ["put", "-c"]
        command += local_paths
        command += (
            []
            if remote_path is None
            else [
                clean_remote_path(
                    remote_path, ensure_trailing_slash=(len(local_paths) > 1)
                )
            ]
        )
        res = self._run_mega_cmd(command)

        if res.return_code == 0:
            if "Upload finished" in res.stdout:
                return True

        elif res.return_code != 0:
            LOGGER.error("Failed to put file/folder:\n" + res.stderr)
            return False

        raise RuntimeError("Unexpected output from put command:\n" + res.stdout)

    def cmd_pwd(self) -> str:
        """Get current remote directory.

        Returns:
            str: Current remote directory path.

        Raises:
            RuntimeError: If the command fails.
        """
        command = ["pwd"]
        res = self._run_mega_cmd(command)
        if res.return_code == 0:
            return res.stdout.strip()

        raise RuntimeError(f"Failed to get current directory: {res.stderr}")

    def cmd_session(self) -> str | None:
        """Get the current session string.

        Returns:
            str | None: Session if logged in, None otherwise.

        TODO: Untested: session when logged in not as user (exported folder link, password protected link).
        """
        res = self._run_mega_cmd(["session"])

        if res.return_code == 0:
            match = self.RE_SESSION.search(res.stdout)
            if match:
                return match.group(1)

        else:  # res.return_code != 0
            if "Not logged in" in res.stderr:
                return None

        raise NotImplementedError(
            "Unexpected output from session command:\n" + res.stdout
        )

    def cmd_tree(self, remote_path: Optional[str] = None) -> str:
        """Get the remote directory tree structure.

        Args:
            remote_path (Optional[str]): Remote path to get tree from. If None, tree under current remote directory. Defaults to None.
        Returns:
            str: Directory tree structure as a string.
        """
        command = ["tree"] + (
            [] if remote_path is None else [clean_remote_path(remote_path)]
        )
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
        res = self._run_mega_cmd(["version"])
        return res.stdout.strip()

    def cmd_whoami(self) -> str | None:
        """
        Get the current logged in user.

        Returns:
            str | None: Logged in user email or None if not logged in.
        """
        res = self._run_mega_cmd(["whoami"])

        # Not logged in or error
        if res.return_code != 0:
            return None

        # Email (logged-in user)
        match = self.RE_WHOAMI_EMAIL.search(res.stdout)
        if match:
            return match.group(1)

        # Misc
        raise NotImplementedError(
            "Unexpected output from whoami command:\n" + res.stdout
        )
