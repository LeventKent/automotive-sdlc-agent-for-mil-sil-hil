# ecu.test reference

## Paths

Default installation paths:

- Global installation: `C:\Program Files\ecu.test <version>`
- Per-user installation: `C:\Users\<user>\AppData\Local\ecu.test <version>`

The `<version>` placeholder uses only major and minor version numbers (no patch version).

Example:

- ecu.test 2026.1.0 and ecu.test 2026.1.3 both install to `ecu.test 2026.1`

## License

Licensing uses an RLM server.

Provide the license string through the `TRACET_LICENSE` environment variable.

Format:

`port@host@user@password`

`user` and `password` are optional.

Examples:

- Without user and password: `5053@rlm.example.com`
- With user and password: `5053@rlm.example.com@Alice@s3cr3t`

## Smoke testing

Always set `--startupAutomated=True` to prevent unwanted GUI windows.

For smoke testing, the preferred option is `ecu.test.exe --kill`.

This command does not start the ecu.test UI, but it still initializes the runtime briefly and performs a license check.

Recommended command:

```powershell
$p = Start-Process ecu.test.exe -ArgumentList '--kill','--startupAutomated=True' -Wait -PassThru
echo $p.ExitCode
```

Exit codes:

- `0`: Success.
- `99`: No license found
