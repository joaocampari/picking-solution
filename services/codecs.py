def row_to_letter(row_index: int) -> str:
    """Converte índice de linha (1..24) para letra (A..X)."""
    if row_index < 1:
        row_index = 1
    # Limitar a 26 letras caso extrapole
    row_index = min(row_index, 26)
    return chr(ord('A') + row_index - 1)


def letter_to_row(letter: str) -> int:
    """Converte letra (A..Z) para índice de linha (1..26)."""
    if not letter:
        return 1
    ch = letter.strip().upper()[0]
    if 'A' <= ch <= 'Z':
        return ord(ch) - ord('A') + 1
    return 1
