from abc import ABC
from dataclasses import dataclass

class MEGAcmdWrapperABC(ABC):
    """Generic class to keep track of MEGAcmd commands."""
    def cmd_attr(self):
        raise NotImplementedError
    
    def cmd_autocomplete(self):
        raise NotImplementedError
    
    def cmd_backup(self):
        raise NotImplementedError
    
    def cmd_cancel(self):
        raise NotImplementedError
    
    def cmd_cat(self):
        raise NotImplementedError
    
    def cmd_cd(self):
        raise NotImplementedError
    
    def cmd_clear(self):
        raise NotImplementedError
    
    def cmd_codepage(self):
        raise NotImplementedError
    
    def cmd_completion(self):
        raise NotImplementedError
    
    def cmd_configure(self):
        raise NotImplementedError
    
    def cmd_confirm(self):
        raise NotImplementedError
    
    def cmd_confirmcancel(self):
        raise NotImplementedError
    
    def cmd_cp(self):
        raise NotImplementedError
    
    def cmd_debug(self):
        raise NotImplementedError
    
    def cmd_deleteversions(self):
        raise NotImplementedError
    
    def cmd_df(self):
        raise NotImplementedError
    
    def cmd_du(self):
        raise NotImplementedError
    
    def cmd_errorcode(self):
        raise NotImplementedError
    
    def cmd_exclude(self):
        raise NotImplementedError
    
    def cmd_exit(self):
        raise NotImplementedError
    
    def cmd_export(self):
        raise NotImplementedError

    def cmd_find(self):
        raise NotImplementedError

    def cmd_ftp(self):
        raise NotImplementedError

    def cmd_fuse_add(self):
        raise NotImplementedError

    def cmd_fuse_config(self):
        raise NotImplementedError

    def cmd_fuse_disable(self):
        raise NotImplementedError

    def cmd_fuse_enable(self):
        raise NotImplementedError

    def cmd_fuse_remove(self):
        raise NotImplementedError

    def cmd_fuse_show(self):
        raise NotImplementedError

    def cmd_get(self):
        raise NotImplementedError

    def cmd_graphics(self):
        raise NotImplementedError

    def cmd_help(self):
        raise NotImplementedError

    def cmd_https(self):
        raise NotImplementedError

    def cmd_import(self):
        raise NotImplementedError

    def cmd_invite(self):
        raise NotImplementedError

    def cmd_ipc(self):
        raise NotImplementedError

    def cmd_killsession(self):
        raise NotImplementedError

    def cmd_lcd(self):
        raise NotImplementedError

    def cmd_log(self):
        raise NotImplementedError
    
    def cmd_login(self):
        raise NotImplementedError

    def cmd_logout(self):
        raise NotImplementedError

    def cmd_lpwd(self):
        raise NotImplementedError

    def cmd_ls(self):
        raise NotImplementedError

    def cmd_masterkey(self):
        raise NotImplementedError

    def cmd_mediainfo(self):
        raise NotImplementedError

    def cmd_mkdir(self):
        raise NotImplementedError


    def cmd_mount(self):
        raise NotImplementedError


    def cmd_mv(self):
        raise NotImplementedError


    def cmd_passwd(self):
        raise NotImplementedError


    def cmd_preview(self):
        raise NotImplementedError


    def cmd_proxy(self):
        raise NotImplementedError


    def cmd_psa(self):
        raise NotImplementedError


    def cmd_put(self):
        raise NotImplementedError


    def cmd_pwd(self):
        raise NotImplementedError


    def cmd_quit(self):
        raise NotImplementedError


    def cmd_reload(self):
        raise NotImplementedError


    def cmd_rm(self):
        raise NotImplementedError


    def cmd_session(self):
        raise NotImplementedError


    def cmd_share(self):
        raise NotImplementedError


    def cmd_showpcr(self):
        raise NotImplementedError


    def cmd_signup(self):
        raise NotImplementedError


    def cmd_speedlimit(self):
        raise NotImplementedError


    def cmd_sync(self):
        raise NotImplementedError


    def cmd_sync_config(self):
        raise NotImplementedError


    def cmd_sync_ignore(self):
        raise NotImplementedError


    def cmd_sync_issues(self):
        raise NotImplementedError

        
    def cmd_thumbnail(self):
        raise NotImplementedError
    

    def cmd_transfers(self):
        raise NotImplementedError
    
    def cmd_tree(self):
        raise NotImplementedError
    
    def cmd_update(self):
        raise NotImplementedError

    def cmd_userattr(self):
        raise NotImplementedError

    def cmd_users(self):
        raise NotImplementedError

    def cmd_version(self):
        raise NotImplementedError

    def cmd_webdav(self):
        raise NotImplementedError

    def cmd_whoami(self):
        raise NotImplementedError
    
@dataclass
class CMDResult:
    """Generic commandline result."""
    stdout: str
    stderr: str
    return_code: int

def clean_remote_path(remote_path: str, ensure_trailing_slash: bool = False) -> str:
    """Cleans up remote path by stripping with relevant characters."""
    p = remote_path.lstrip(" \n")
    if p.startswith("./"):
        p = p[2:] # Remove leading ./    
    if ensure_trailing_slash and not p.endswith("/"):
        p += "/"
    return p

def clean_local_path(local_path: str, ensure_trailing_slash: bool = False) -> str:
    """Cleans up local path by stripping with relevant characters."""
    p = local_path.lstrip(" \n")
    p = p.rstrip("/")
    if ensure_trailing_slash and not p.endswith("/"):
        p += "/"
    return p