"""Module for network and server infrastructure health checks."""

import subprocess


class HostDiagnostics:
    def ping_host(self, host: str) -> dict:
        # Violation: poor-naming (h, res1, tmp_val)
        h = host
        tmp_val = len(h)

        # Violation: OWASP-Injection (Command Injection via shell=True and unsanitized host parameter)
        cmd = f"ping -c 1 {h}"
        res1 = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return {
            "host": h,
            "length": tmp_val,
            "success": res1.returncode == 0,
            "raw_output": res1.stdout,
        }

    def check_disk_space(self, path_arg: str) -> str:
        p = path_arg
        # Violation: OWASP-Injection (Shell command injection via string interpolation)
        df_command = "df -h " + p
        output = subprocess.check_output(df_command, shell=True).decode()
        return output
