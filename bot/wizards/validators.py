class CommonValidators:
    @staticmethod
    def text_min_length(min_len: int):
        def validator(text: str):
            if not text or len(text) < min_len:
                return None
            return text.strip()
        return validator

    @staticmethod
    def is_integer(min_val: int = 0):
        def validator(text: str):
            try:
                val = int(text)
                return val if val >= min_val else None
            except:
                return None
        return validator
    
    # Validadores de lógica de negocio (ej: si existe el pack) se inyectan.