/*
    YARA rule for detecting suspicious image patterns
*/

rule SuspiciousImageSteganography
{
    meta:
        description = "Detects potential steganography in images"
        author = "Security Team"
        severity = "medium"
        reference = "Internal security guidelines"
        
    strings:
        $outguess = "outguess" nocase
        $steghide = "steghide" nocase
        $stegdetect = "stegdetect" nocase
        $lsb = "LSB" nocase
        $stegano = "stegano" nocase
        
    condition:
        2 of them
}

rule SuspiciousImageMetadata
{
    meta:
        description = "Detects suspicious metadata in images"
        author = "Security Team"
        severity = "low"
        reference = "Internal security guidelines"
        
    strings:
        $script = "script" nocase
        $javascript = "javascript" nocase
        $php = "php" nocase
        $html = "<html" nocase
        $url = "http://" nocase
        $url2 = "https://" nocase
        $iframe = "iframe" nocase
        $exec = "exec" nocase
        
    condition:
        3 of them
}

rule PotentiallyModifiedImage
{
    meta:
        description = "Detects potentially modified image headers"
        author = "Security Team"
        severity = "medium"
        reference = "Internal security guidelines"
        
    condition:
        // JPEG with incorrect header
        (uint16(0) == 0xD8FF and not uint32(0) == 0xE0FFD8FF and not uint32(0) == 0xE1FFD8FF) or
        // PNG with incorrect header
        (uint32(0) == 0x474E5089 and not uint32(4) == 0x0A1A0A0D)
}
