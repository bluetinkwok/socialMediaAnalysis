/*
 * Basic YARA rules for detecting suspicious patterns in files
 * These rules are used by the pattern_detector module
 */

rule Suspicious_PowerShell_Commands {
    meta:
        description = "Detects suspicious PowerShell commands often used in malicious scripts"
        author = "Social Media Analysis Platform"
        severity = "medium"
    
    strings:
        $invoke_expression = "Invoke-Expression" nocase
        $invoke_webrequest = "Invoke-WebRequest" nocase
        $invoke_obfuscation = "Invoke-Obfuscation" nocase
        $download_string = "DownloadString" nocase
        $hidden_window = "-WindowStyle Hidden" nocase
        $encoded_command = "-EncodedCommand" nocase
        $bypass = "-ExecutionPolicy Bypass" nocase
        $web_client = "New-Object Net.WebClient" nocase
        $shell_execute = "[System.Diagnostics.Process]::Start" nocase
    
    condition:
        3 of them
}

rule Suspicious_JavaScript {
    meta:
        description = "Detects suspicious JavaScript patterns often found in malicious scripts"
        author = "Social Media Analysis Platform"
        severity = "medium"
    
    strings:
        $eval = "eval(" nocase
        $fromcharcode = "fromCharCode" nocase
        $document_write = "document.write" nocase
        $unescape = "unescape(" nocase
        $atob = "atob(" nocase
        $iframe = "createElement('iframe')" nocase
        $hidden_iframe = /iframe.style.display\s*=\s*['"]none['"]/ nocase
        $obfuscated_function = /function\s*\w{1,2}\(/
        $long_string = /"[^"]{1000,}"/ // Very long strings are suspicious
    
    condition:
        3 of them
}

rule Suspicious_PHP_Code {
    meta:
        description = "Detects suspicious PHP code patterns often found in web shells and malicious scripts"
        author = "Social Media Analysis Platform"
        severity = "high"
    
    strings:
        $php_tag = "<?php" nocase
        $system = "system(" nocase
        $exec = "exec(" nocase
        $shell_exec = "shell_exec(" nocase
        $passthru = "passthru(" nocase
        $eval = "eval(" nocase
        $base64_decode = "base64_decode(" nocase
        $gzinflate = "gzinflate(" nocase
        $preg_replace_eval = "preg_replace" nocase
        $assert = "assert(" nocase
        $include_url = "include('http" nocase
        $request_var = "$_REQUEST" nocase
        $get_var = "$_GET" nocase
        $post_var = "$_POST" nocase
    
    condition:
        $php_tag and 3 of them
}

rule Suspicious_Executable_Strings {
    meta:
        description = "Detects suspicious strings commonly found in malicious executables"
        author = "Social Media Analysis Platform"
        severity = "medium"
    
    strings:
        $process_injection = "VirtualAlloc" nocase
        $keylogger_api = "GetAsyncKeyState" nocase
        $screenshot_api = "BitBlt" nocase
        $persistence = "CurrentVersion\\Run" nocase
        $disable_defender = "DisableAntiSpyware" nocase
        $disable_firewall = "netsh firewall set opmode disable" nocase
        $suspicious_url = /https?:\/\/[^\s\/$.?#].[^\s]*\.(xyz|top|club|pw|cc|su|gq|ga)/ nocase
        $suspicious_domain = /(\.bit|\.onion)/ nocase
        $tor_service = "127.0.0.1:9050" nocase
    
    condition:
        3 of them
}

rule EICAR_Test_File {
    meta:
        description = "This is a rule to detect the EICAR test file"
        author = "Social Media Analysis Platform"
        severity = "info"
    
    strings:
        $eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    
    condition:
        $eicar
}

rule Hidden_Scripts_In_Images {
    meta:
        description = "Detects scripts hidden in images (polyglot files)"
        author = "Social Media Analysis Platform"
        severity = "high"
    
    strings:
        $php = "<?php"
        $script = "<script"
        $html = "<html"
        $eval = "eval("
        $jpeg_header = { FF D8 FF }
        $png_header = { 89 50 4E 47 }
        $gif_header = { 47 49 46 38 }
    
    condition:
        ($jpeg_header at 0 or $png_header at 0 or $gif_header at 0) and
        ($php or $script or $html or $eval)
}

rule Suspicious_Office_Macros {
    meta:
        description = "Detects suspicious patterns in Office documents that may contain malicious macros"
        author = "Social Media Analysis Platform"
        severity = "medium"
    
    strings:
        $auto_open = "Auto_Open" nocase
        $auto_exec = "AutoExec" nocase
        $auto_exit = "Auto_Exit" nocase
        $auto_close = "Auto_Close" nocase
        $document_open = "Document_Open" nocase
        $workbook_open = "Workbook_Open" nocase
        $shell = "Shell(" nocase
        $wscript = "WScript.Shell" nocase
        $powershell = "powershell" nocase
        $hidden = "WindowStyle Hidden" nocase
        $create_object = "CreateObject" nocase
        $chr_obfuscation = /Chr\(\d+\)\s*&\s*Chr\(\d+\)/ nocase
    
    condition:
        3 of them
} 