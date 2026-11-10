class FormValidator:
    @staticmethod
    def is_valid_symbol(symbol: str) -> tuple[bool, str]:
        sym = symbol.strip().upper()
        if not sym:
            return False, "Stock ya ETF symbol khali nahi ho sakta!"
        if not sym.isalnum():
            return False, "Symbol mein sirf alphabets aur numbers hone chahiye!"
        return True, sym

    @staticmethod
    def is_positive_number(value_str: str, field_name: str) -> tuple[bool, float]:
        try:
            val = float(value_str.strip())
            if val <= 0:
                return False, f"{field_name} 0 se bada hona chahiye!"
            return True, val
        except ValueError:
            return False, f"{field_name} mein ek valid number darj karein!"

    @staticmethod
    def is_positive_int(value_str: str, field_name: str) -> tuple[bool, int]:
        try:
            val = int(value_str.strip())
            if val <= 0:
                return False, f"{field_name} 0 se badi quantity honi chahiye!"
            return True, val
        except ValueError:
            return False, f"{field_name} mein ek valid integer quantity darj karein!"
