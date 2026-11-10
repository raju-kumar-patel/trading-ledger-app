import re

def validate_pan(pan):
    """
    Indian PAN Card format check karta hai: 
    5 Letters, 4 Digits, 1 Letter (e.g., ABCDE1234F)
    """
    pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    return bool(re.match(pattern, pan.strip().upper()))

def validate_pin(pin):
    """
    PIN strictly 4-digit numeric hona chahiye
    """
    pattern = r"^\d{4}$"
    return bool(re.match(pattern, pin.strip()))
