/*
    YARA rule for detecting potentially malicious code patterns
*/

rule PotentialShellcode
{
    meta:
        description = "Detects potential shellcode patterns"
        author = "Security Team"
        severity = "high"
        reference = "Internal security guidelines"
        
    strings:
        $shellcode1 = { 31 C0 50 68 2F 2F 73 68 68 2F 62 69 6E 89 E3 50 53 89 E1 B0 0B CD 80 }  // Linux /bin/sh shellcode
        $shellcode2 = { FC E8 82 00 00 00 60 89 E5 31 C0 64 8B 50 30 8B 52 0C }  // Windows shellcode pattern
        
    condition:
        any of them
}

rule PotentialWebShell
{
    meta:
        description = "Detects potential web shell patterns"
        author = "Security Team"
        severity = "high"
        reference = "Internal security guidelines"
        
    strings:
        $php_shell1 = "eval($_" nocase
        $php_shell2 = "system($_" nocase
        $php_shell3 = "shell_exec($_" nocase
        $php_shell4 = "passthru($_" nocase
        $php_shell5 = "exec($_" nocase
        $asp_shell1 = "eval(Request" nocase
        $asp_shell2 = "execute(Request" nocase
        
    condition:
        any of them
}

rule SuspiciousJavaScript
{
    meta:
        description = "Detects suspicious JavaScript patterns"
        author = "Security Team"
        severity = "medium"
        reference = "Internal security guidelines"
        
    strings:
        $eval = "eval(" nocase
        $doc_write = "document.write(unescape(" nocase
        $fromCharCode = "String.fromCharCode(" nocase
        $decode = ".decode" nocase
        $obfuscated1 = /\\x[0-9a-f]{2}/i
        $obfuscated2 = /\\\d{3}/
        
    condition:
        3 of them
}

rule SuspiciousPDF
{
    meta:
        description = "Detects suspicious PDF patterns"
        author = "Security Team"
        severity = "medium"
        reference = "Internal security guidelines"
        
    strings:
        $js = "/JS" nocase
        $javascript = "/JavaScript" nocase
        $openaction = "/OpenAction" nocase
        $launch = "/Launch" nocase
        $action = "/AA" nocase
        $embed = "/EmbeddedFile" nocase
        
    condition:
        uint32(0) == 0x46445025 and // %PDF
        2 of them
}

rule SuspiciousOfficeDocument
{
    meta:
        description = "Detects suspicious Office document patterns"
        author = "Security Team"
        severity = "medium"
        reference = "Internal security guidelines"
        
    strings:
        $macro = "VBA" nocase
        $auto_open = "Auto_Open" nocase
        $auto_exec = "AutoExec" nocase
        $auto_exec2 = "AutoOpen" nocase
        $powershell = "powershell" nocase
        $cmd = "cmd.exe" nocase
        $wscript = "WScript.Shell" nocase
        
    condition:
        2 of them
}
