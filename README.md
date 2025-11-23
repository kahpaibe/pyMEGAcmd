# pyMEGAcmd

A Python (partial) wrapper for the [MEGAcmd](https://github.com/meganz/MEGAcmd/tree/master) command-line client.

## Requirements
- Python 3.10+
- [MEGAcmd](https://github.com/meganz/MEGAcmd/tree/master) installed

## Example Usage

```python
from pyMEGAcmd import MEGAcmdWrapper

if __name__ == '__main__':
    MEGA_PATH = "MEGAclient.exe"
    mega = MEGAcmdWrapper(mega_path=MEGA_PATH)
    username = input("Enter MEGA email: ")
    password = input("Enter MEGA password: ")
    print("Login:", mega.cmd_login(username, password))
    
    print("Whoami:", mega.cmd_whoami())
    print("Tree: \n", mega.cmd_tree("/"))
    
    print("Logout:", mega.cmd_logout())
```

## Current Features

The wrapper currently supports the following MEGAcmd commands:
- `cat`
- `cd`
- `cp`
- `df`
- `du`
- `export`
- `find`
- `get`
- `import`
- `login` (partial)
- `logout`
- `lcd`
- `lpwd`
- `ls`
- `mkdir`
- `mv`
- `put`
- `pwd`
- `rm`
- `session`
- `tree`
- `version`
- `whoami`

## TODO
- Implement additional MEGAcmd commands
- Add support for pcre for commands that support it
- Homogenize error handling and exceptions (use more raise), provide new Exception class with `error_code` attribute

## License

See [LICENSE](./LICENSE) for details.